"""Тесты Ode KitAi. Запуск: python3 -m unittest discover -s tests -v

Сетевые вызовы не делаются: провайдеры подменяются заглушками.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from kitai import config as cfg  # noqa: E402
from kitai import mods as mods_mod  # noqa: E402
from kitai.providers import Provider, ProviderError, load_providers  # noqa: E402
from kitai.strategy import Router, StrategyConfig, build_system_prompt  # noqa: E402


class TestConfig(unittest.TestCase):
    def test_parse_env_handles_comments_quotes_and_export(self):
        text = "\n".join(
            [
                "# комментарий",
                "",
                "GROQ_API_KEY=abc123",
                'GEMINI_API_KEY="quoted"',
                "export OPENROUTER_API_KEY='single'",
                "BROKEN_LINE_NO_EQUALS",
            ]
        )
        parsed = cfg.parse_env_text(text)
        self.assertEqual(parsed["GROQ_API_KEY"], "abc123")
        self.assertEqual(parsed["GEMINI_API_KEY"], "quoted")
        self.assertEqual(parsed["OPENROUTER_API_KEY"], "single")
        self.assertNotIn("BROKEN_LINE_NO_EQUALS", parsed)

    def test_mask_secret_never_leaks_full_key(self):
        # Строка намеренно не похожа на настоящий ключ провайдера,
        # чтобы сканеры секретов не срабатывали на тестовый файл.
        secret = "FAKE" + "-" + "not-a-real-key-0000000000"
        masked = cfg.mask_secret(secret)
        self.assertNotIn(secret, masked)
        self.assertIn("FAKE", masked)
        self.assertIn("длина", masked)

    def test_mask_secret_empty(self):
        self.assertEqual(cfg.mask_secret(None), "не задан")
        self.assertEqual(cfg.mask_secret(""), "не задан")

    def test_is_secret_name(self):
        self.assertTrue(cfg.is_secret_name("GROQ_API_KEY"))
        self.assertTrue(cfg.is_secret_name("GITHUB_MODELS_TOKEN"))
        self.assertFalse(cfg.is_secret_name("OLLAMA_URL"))


class TestProvidersConfig(unittest.TestCase):
    def setUp(self):
        self.providers = load_providers()

    def test_all_expected_providers_present(self):
        for expected in ("ollama", "groq", "gemini", "github_models", "openrouter"):
            self.assertIn(expected, self.providers)

    def test_local_provider_needs_no_key(self):
        ollama = self.providers["ollama"]
        self.assertTrue(ollama.is_local)
        self.assertFalse(ollama.api_key_required)
        self.assertTrue(ollama.is_ready())

    def test_cloud_providers_declare_key_env_and_docs(self):
        for provider in self.providers.values():
            if provider.is_local:
                continue
            self.assertTrue(provider.api_key_env, f"{provider.id} без api_key_env")
            self.assertTrue(provider.docs.startswith("http"), f"{provider.id} без ссылки на доки")
            self.assertTrue(provider.signup, f"{provider.id} без инструкции регистрации")

    def test_no_secret_values_stored_in_config(self):
        raw = cfg.PROVIDERS_FILE.read_text(encoding="utf-8")
        for leak in ("gsk_", "sk-or-v1", "AIza", "ghp_"):
            self.assertNotIn(leak, raw, f"В конфиге найден похожий на ключ текст: {leak}")

    def test_base_url_env_override(self):
        provider = Provider(
            id="ollama",
            title="t",
            kind="local",
            base_url="http://localhost:11434/v1",
            default_model="m",
            base_url_env="TEST_OLLAMA_URL",
        )
        import os

        os.environ["TEST_OLLAMA_URL"] = "http://192.168.1.50:11434"
        try:
            self.assertEqual(provider.resolved_base_url(), "http://192.168.1.50:11434/v1")
        finally:
            del os.environ["TEST_OLLAMA_URL"]


class TestStrategy(unittest.TestCase):
    def setUp(self):
        self.strategy = StrategyConfig.load()

    def test_profiles_exist_and_active_is_valid(self):
        self.assertIn(self.strategy.active_profile, self.strategy.profiles)
        for expected in ("balanced", "fast_free", "private_local", "android", "deep_research"):
            self.assertIn(expected, self.strategy.profiles)

    def test_every_chain_step_references_known_provider(self):
        providers = load_providers()
        for profile in self.strategy.profiles.values():
            self.assertTrue(profile.chain, f"профиль {profile.name} с пустой цепочкой")
            for step in profile.chain:
                self.assertIn(step.provider, providers, f"{profile.name}: {step.provider}")

    def test_private_profile_is_local_only(self):
        profile = self.strategy.profiles["private_local"]
        providers = load_providers()
        self.assertFalse(profile.allow_cloud)
        for step in profile.chain:
            self.assertTrue(providers[step.provider].is_local)

    def test_cloud_profiles_end_with_local_fallback(self):
        providers = load_providers()
        for name in ("balanced", "fast_free", "deep_research"):
            chain = self.strategy.profiles[name].chain
            self.assertTrue(
                providers[chain[-1].provider].is_local,
                f"профиль {name} не имеет локальной страховки в конце",
            )

    def test_model_preference_warns_on_avoided_family(self):
        warning = self.strategy.check_model_preference("qwen/qwen3-32b")
        self.assertIsNotNone(warning)
        self.assertIn("qwen", warning.lower())
        self.assertIsNone(self.strategy.check_model_preference("llama-3.1-8b-instant"))

    def test_no_avoided_family_in_any_default_chain(self):
        avoided = self.strategy.avoided_families()
        for profile in self.strategy.profiles.values():
            for step in profile.chain:
                if step.model:
                    for family in avoided:
                        self.assertNotIn(family, step.model.lower())

    def test_system_prompt_reflects_settings(self):
        prompt = build_system_prompt(self.strategy)
        self.assertIn("русском", prompt)
        self.assertIn("qwen", prompt.lower())
        self.assertIn("ВНИМАНИЕ", prompt)

    def test_system_prompt_short_mode_has_no_strategist_block(self):
        prompt = build_system_prompt(self.strategy, strategist=False)
        self.assertNotIn("ВНИМАНИЕ", prompt)


class FakeChat:
    """Заглушка сети: отвечает по сценарию, считает вызовы."""

    def __init__(self, script):
        self.script = dict(script)
        self.calls = []

    def __call__(self, provider, messages, *, model=None, timeout=120, temperature=0.3, max_tokens=1200):
        self.calls.append(provider.id)
        outcome = self.script.get(provider.id, "ok")
        if isinstance(outcome, ProviderError):
            raise outcome
        return {
            "provider": provider.id,
            "model": model or provider.default_model,
            "content": f"ответ от {provider.id}",
            "elapsed": 0.1,
            "prompt_tokens": 10,
            "completion_tokens": 5,
        }


class TestRouter(unittest.TestCase):
    def setUp(self):
        self.providers = load_providers()
        # Делаем облачных провайдеров "готовыми" без настоящих ключей.
        import os

        self._saved = {}
        for provider in self.providers.values():
            if provider.api_key_env:
                self._saved[provider.api_key_env] = os.environ.get(provider.api_key_env)
                os.environ[provider.api_key_env] = "test-key-not-real"
        self.strategy = StrategyConfig.load()

    def tearDown(self):
        import os

        for name, value in self._saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def _router(self, script):
        fake = FakeChat(script)
        return Router(providers=self.providers, strategy=self.strategy, chat_fn=fake), fake

    def test_first_provider_wins(self):
        router, fake = self._router({})
        result = router.run([{"role": "user", "content": "hi"}], profile_name="balanced")
        self.assertTrue(result.ok)
        self.assertEqual(result.provider, "groq")
        self.assertEqual(len(fake.calls), 1)

    def test_falls_through_on_rate_limit(self):
        script = {"groq": ProviderError("лимит исчерпан (429)", status=429, retryable=True)}
        router, fake = self._router(script)
        self.strategy.runtime["max_retries_per_step"] = 0
        result = router.run([{"role": "user", "content": "hi"}], profile_name="balanced")
        self.assertTrue(result.ok)
        self.assertEqual(result.provider, "gemini")
        self.assertEqual(fake.calls[0], "groq")
        self.assertIn("429", result.attempts[0].detail)

    def test_falls_all_the_way_to_local(self):
        error = ProviderError("нет связи", retryable=True)
        script = {
            "groq": error,
            "gemini": error,
            "github_models": error,
            "openrouter": error,
        }
        router, _ = self._router(script)
        self.strategy.runtime["max_retries_per_step"] = 0
        result = router.run([{"role": "user", "content": "hi"}], profile_name="balanced")
        self.assertTrue(result.ok)
        self.assertEqual(result.provider, "ollama")

    def test_all_fail_returns_readable_explain(self):
        error = ProviderError("всё сломалось", retryable=False)
        script = {p: error for p in self.providers}
        router, _ = self._router(script)
        self.strategy.runtime["max_retries_per_step"] = 0
        result = router.run([{"role": "user", "content": "hi"}], profile_name="balanced")
        self.assertFalse(result.ok)
        self.assertIn("всё сломалось", result.explain())

    def test_private_profile_never_calls_cloud(self):
        router, fake = self._router({})
        result = router.run([{"role": "user", "content": "hi"}], profile_name="private_local")
        self.assertTrue(result.ok)
        self.assertEqual(fake.calls, ["ollama"])

    def test_provider_override(self):
        router, fake = self._router({})
        result = router.run([{"role": "user", "content": "hi"}], provider_override="gemini")
        self.assertTrue(result.ok)
        self.assertEqual(fake.calls, ["gemini"])

    def test_unknown_provider_override_raises(self):
        router, _ = self._router({})
        with self.assertRaises(KeyError):
            router.run([{"role": "user", "content": "hi"}], provider_override="nonexistent")

    def test_plan_marks_missing_key_as_not_ready(self):
        import os

        os.environ.pop("GROQ_API_KEY", None)
        providers = load_providers()
        router = Router(providers=providers, strategy=self.strategy, chat_fn=FakeChat({}))
        rows = {row["provider"]: row for row in router.plan("balanced")}
        self.assertFalse(rows["groq"]["ready"])
        self.assertTrue(rows["ollama"]["ready"])


class TestMods(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.registry = mods_mod.load_registry()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_registry_loads_builtin_and_repo_mods(self):
        self.assertIn("web-fetch", self.registry)
        self.assertIn("notes", self.registry)
        self.assertIn("open-webui", self.registry)

    def test_every_builtin_plugin_file_exists(self):
        for mod in self.registry.values():
            if mod.type == "plugin" and mod.source == "builtin":
                path = mods_mod.BUILTIN_DIR / mod.file
                self.assertTrue(path.is_file(), f"нет файла мода: {path}")

    def test_install_plugin_copies_file(self):
        mod = self.registry["notes"]
        target = mods_mod.install_plugin_mod(mod, plugin_dir=self.tmp)
        self.assertTrue(target.is_file())
        self.assertIn("COMMAND", target.read_text(encoding="utf-8"))

    def test_install_plugin_twice_needs_force(self):
        mod = self.registry["notes"]
        mods_mod.install_plugin_mod(mod, plugin_dir=self.tmp)
        with self.assertRaises(mods_mod.ModError):
            mods_mod.install_plugin_mod(mod, plugin_dir=self.tmp)
        mods_mod.install_plugin_mod(mod, plugin_dir=self.tmp, force=True)

    def test_rejects_non_https_and_unknown_hosts(self):
        with self.assertRaises(mods_mod.ModError):
            mods_mod.validate_git_url("http://github.com/user/repo.git")
        with self.assertRaises(mods_mod.ModError):
            mods_mod.validate_git_url("https://evil.example.com/user/repo.git")
        with self.assertRaises(mods_mod.ModError):
            mods_mod.validate_git_url("https://github.com/onlyuser")
        mods_mod.validate_git_url("https://github.com/open-webui/open-webui.git")

    def test_default_repo_name(self):
        self.assertEqual(
            mods_mod.default_repo_name("https://github.com/open-webui/open-webui.git"),
            "open-webui",
        )

    def test_repo_clone_is_not_executed_only_downloaded(self):
        calls = []

        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        def fake_runner(cmd, **kwargs):
            calls.append(cmd)
            Path(cmd[-1]).mkdir(parents=True, exist_ok=True)
            return Result()

        mod = self.registry["open-webui"]
        mods_mod.install_repo_mod(mod, mods_dir=self.tmp, runner=fake_runner)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][:2], ["git", "clone"])
        # Убеждаемся, что ничего кроме git clone не запускалось.
        for cmd in calls:
            self.assertNotIn("bash", cmd)
            self.assertNotIn("sh", cmd)
            self.assertNotIn("python", cmd)

    def test_unknown_mod_id_raises_with_hint(self):
        with self.assertRaises(mods_mod.ModError) as ctx:
            mods_mod.install("no-such-mod", registry=self.registry)
        self.assertIn("Доступные", str(ctx.exception))


class TestBuiltinModsSafety(unittest.TestCase):
    def test_web_fetch_blocks_private_addresses(self):
        sys.path.insert(0, str(mods_mod.BUILTIN_DIR))
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "web_fetch_test", mods_mod.BUILTIN_DIR / "web_fetch.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self.assertTrue(module._is_private_host("localhost"))
        self.assertTrue(module._is_private_host("127.0.0.1"))
        self.assertIn("только http", module.handle("ftp://example.com", {}).lower())
        self.assertIn("локальную сеть", module.handle("http://127.0.0.1:8080", {}))

    def test_all_builtin_mods_have_required_interface(self):
        import importlib.util

        for path in mods_mod.BUILTIN_DIR.glob("*.py"):
            if path.name == "__init__.py":
                continue
            spec = importlib.util.spec_from_file_location(f"mod_{path.stem}", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertTrue(hasattr(module, "COMMAND"), f"{path.name} без COMMAND")
            self.assertTrue(hasattr(module, "HELP"), f"{path.name} без HELP")
            self.assertTrue(callable(module.handle), f"{path.name} без handle()")


class TestCli(unittest.TestCase):
    def test_parser_builds_and_known_commands_exist(self):
        import kitai_cli

        parser = kitai_cli.build_parser()
        for command in ("setup", "providers", "key", "strategy", "mods", "doctor", "ask"):
            args = parser.parse_args([command] if command != "ask" else ["ask", "привет"])
            self.assertTrue(hasattr(args, "func"))

    def test_ask_requires_question(self):
        import kitai_cli

        parser = kitai_cli.build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["ask"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
