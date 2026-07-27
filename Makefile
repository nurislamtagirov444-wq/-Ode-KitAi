SDK_URL = https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
SDK_DIR = $(PWD)/android-sdk
GRADLE_VERSION = 8.7
GRADLE_URL = https://services.gradle.org/distributions/gradle-$(GRADLE_VERSION)-bin.zip
GRADLE_DIR = $(PWD)/gradle-$(GRADLE_VERSION)
GRADLE_BIN = $(GRADLE_DIR)/bin/gradle

.PHONY: build-apk clean

build-apk: $(SDK_DIR)/cmdline-tools/latest/bin/sdkmanager $(GRADLE_BIN)
	@echo "Accepting Android SDK licenses..."
	yes | $(SDK_DIR)/cmdline-tools/latest/bin/sdkmanager --sdk_root=$(SDK_DIR) --licenses > /dev/null
	@echo "Building APKs with Gradle..."
	cd test-apk && ANDROID_HOME=$(SDK_DIR) $(GRADLE_BIN) assembleDebug
	cp test-apk/app/build/outputs/apk/debug/app-debug.apk web/AIAppManager.apk
	cp test-apk/app/build/outputs/apk/debug/app-debug.apk web/AnimeNovel.apk
	@echo "Done! web/AIAppManager.apk and web/AnimeNovel.apk are ready."

$(SDK_DIR)/cmdline-tools/latest/bin/sdkmanager:
	@echo "Downloading Android SDK Command Line Tools..."
	mkdir -p $(SDK_DIR)/cmdline-tools
	wget -qO cmdline-tools.zip $(SDK_URL) || curl -sLo cmdline-tools.zip $(SDK_URL)
	unzip -q cmdline-tools.zip -d $(SDK_DIR)/cmdline-tools
	rm cmdline-tools.zip
	mv $(SDK_DIR)/cmdline-tools/cmdline-tools $(SDK_DIR)/cmdline-tools/latest

$(GRADLE_BIN):
	@echo "Downloading Gradle $(GRADLE_VERSION)..."
	wget -qO gradle.zip $(GRADLE_URL) || curl -sLo gradle.zip $(GRADLE_URL)
	unzip -q gradle.zip -d $(PWD)
	rm gradle.zip

clean:
	rm -rf $(SDK_DIR) $(GRADLE_DIR) web/AIAppManager.apk web/AnimeNovel.apk
	cd test-apk && rm -rf .gradle app/build build
