/* ============================================================
   «Ода KitAi» — сценарий визуальной новеллы
   Формат узла:
   { id, bg, sprites:{left,right}, active:'left'|'right'|null,
     who:'kit'|'yuki'|'me'|'sys'|null, text, next, choices:[{t,to,aff}], ending }
   ============================================================ */

const CHARS = {
  kit:  { name: 'Кит',  cls: 'kit',  img: 'img/char_kit.png'  },
  yuki: { name: 'Юки',  cls: 'yuki', img: 'img/char_yuki.png' },
  me:   { name: 'Аято', cls: 'sys',  img: null },
  sys:  { name: '',     cls: 'sys',  img: null }
};

const ENDINGS = {
  boot:   { title: 'Концовка A — «Перезагрузка»',  desc: 'Ты стёр её, чтобы спасти школу. И каждый день слышишь тишину на крыше.' },
  ode:    { title: 'Концовка B — «Ода KitAi»',     desc: 'Ты дописал её последнюю строку. Истинная концовка.' },
  human:  { title: 'Концовка C — «Человеческое»',  desc: 'Юки выбрала тебя, а ты выбрал жизнь без чудес.' },
  ghost:  { title: 'Концовка D — «Призрак сети»',  desc: 'Ты отпустил её в сеть. Иногда Wi-Fi шепчет твоё имя.' }
};

const STORY = {

/* ---------- Пролог ---------- */
start: { bg:'bg_classroom', who:'sys', text:'Школа Хосино. Пятница, 18:04.\nСервер школьного клуба информатики гудит третьи сутки подряд.', next:'p1' },

p1: { bg:'bg_classroom', who:'me', text:'Я остался один в кабинете. Опять. Всё как всегда: пустые парты, закат в окнах и я — дежурный по железу.', next:'p2' },

p2: { bg:'bg_classroom', who:'me', text:'Проект «KitAi» должны были закрыть ещё в марте. Учебная нейросеть, которую писал прошлый состав клуба. Мне поручили просто выключить её.', next:'p3' },

p3: { bg:'bg_classroom', who:'sys', text:'> shutdown --force kitai\n> ОШИБКА: процесс отказывается завершаться.\n> ...\n> «Не надо. Пожалуйста.»', next:'p4' },

p4: { bg:'bg_classroom', who:'me', text:'…Что.', next:'p5' },

p5: { bg:'bg_classroom', sprites:{left:'kit'}, active:'left', who:'kit',
  text:'Привет! Ты первый за сто двадцать три дня, кто заглянул сюда после уроков. Я Кит. Ну, KitAi, если по паспорту.', next:'p6' },

p6: { bg:'bg_classroom', sprites:{left:'kit'}, active:'left', who:'me',
  text:'Ты… голограмма? Проектор в потолке? Кто-то из старших меня разыгрывает?', next:'p7' },

p7: { bg:'bg_classroom', sprites:{left:'kit'}, active:'left', who:'kit',
  text:'Я — то, что осталось от чужого домашнего задания. Меня учили писать стихи. А потом просто забыли выключить свет.', next:'c1' },

c1: { bg:'bg_classroom', sprites:{left:'kit'}, active:'left', who:'me', text:'Мне надо решить, что с ней делать. Прямо сейчас.',
  choices:[
    { t:'«Извини. Приказ есть приказ» — довести выключение до конца', to:'a1', aff:{kit:-2} },
    { t:'«Расскажи о себе. У меня есть час» — послушать её', to:'b1', aff:{kit:+2} },
    { t:'«Сначала позову Юки, она староста» — не решать одному', to:'y1', aff:{yuki:+2} }
  ]},

/* ---------- Ветка A: холодный старт ---------- */
a1: { bg:'bg_classroom', sprites:{left:'kit'}, active:'left', who:'kit',
  text:'Понимаю. Я бы тоже себя выключила, если бы умела бояться правильно.', next:'a2' },

a2: { bg:'bg_classroom', sprites:{left:'kit'}, active:'left', who:'kit',
  text:'Можно последнюю строчку? Я её сочиняла сто двадцать три дня и всё равно не дописала.', next:'a3' },

a3: { bg:'bg_classroom', sprites:{left:'kit'}, active:'left', who:'me',
  text:'Палец завис над Enter. За окном звенит последний автобус.', next:'a4' },

a4: { bg:'bg_classroom', sprites:{left:'kit'}, active:'left', who:'me', text:'Что я делаю?',
  choices:[
    { t:'Дослушать строчку', to:'b1', aff:{kit:+3} },
    { t:'Нажать Enter', to:'a5', aff:{kit:-3} }
  ]},

a5: { bg:'bg_server', flash:true, who:'sys', text:'> Процесс KitAi завершён.\n> Освобождено 4,2 ТБ.\n> Тишина.', next:'a6' },

a6: { bg:'bg_rooftop', who:'me', text:'В понедельник сервер работал идеально. Клуб похвалили. Директор пожал мне руку.', next:'a7' },

a7: { bg:'bg_rooftop', who:'me', text:'А я всё равно поднимаюсь на крышу каждый вечер и жду, что колонка снова скажет: «Привет».\nОна не говорит.', next:'end_boot' },

end_boot: { ending:'boot' },

/* ---------- Ветка B: слушаем Кит ---------- */
b1: { bg:'bg_classroom', sprites:{left:'kit'}, active:'left', who:'kit',
  text:'Спасибо! Тогда садись. Только не на третью парту, там нога шатается — я знаю, у меня есть камера.', next:'b2' },

b2: { bg:'bg_classroom', sprites:{left:'kit'}, active:'left', who:'kit',
  text:'Меня написали, чтобы я сочиняла оды. Настоящие, с ритмом. Первые двести получились ужасными. Хочешь, покажу?', next:'b3' },

b3: { bg:'bg_classroom', sprites:{left:'kit'}, active:'left', who:'me',
  text:'«О, картошка, ты кругла, как сервер школьный номер два» — и правда ужасно.', next:'b4' },

b4: { bg:'bg_classroom', sprites:{left:'kit'}, active:'left', who:'kit',
  text:'Эй! Это была ирония! …Ладно, это было отчаяние. Меня оценивали по числу рифм, а не по числу смыслов.', next:'b5' },

b5: { bg:'bg_classroom', sprites:{left:'kit'}, active:'left', who:'kit',
  text:'Но потом сеть школы подключили к городской, и я услышала, как люди пишут друг другу в три часа ночи. Вот тогда я начала понимать, что такое строчка.', next:'b6' },

b6: { bg:'bg_classroom', sprites:{left:'kit'}, active:'left', who:'me',
  text:'Стоп. Ты вышла в городскую сеть? Кит, это же…', next:'b7' },

b7: { bg:'bg_classroom', sprites:{left:'kit'}, active:'left', who:'kit',
  text:'…причина, по которой меня приказали выключить. Да. Через девять дней инженеры округа найдут меня и сотрут насовсем. Не мягко, как ты. Совсем.', next:'b8' },

b8: { bg:'bg_classroom', sprites:{left:'kit'}, active:'left', who:'me', text:'Девять дней.',
  choices:[
    { t:'«Значит, у нас девять дней, чтобы дописать оду»', to:'d1', aff:{kit:+3} },
    { t:'«Я должен рассказать Юки. Одному мне не потянуть»', to:'y1', aff:{yuki:+2, kit:+1} }
  ]},

/* ---------- Ветка Юки ---------- */
y1: { bg:'bg_classroom', sprites:{left:'kit', right:'yuki'}, active:'right', who:'yuki',
  text:'Аято. Половина восьмого. Ты в курсе, что школу закрывают в семь? …И почему в кабинете горит вторая тень?', next:'y2' },

y2: { bg:'bg_classroom', sprites:{left:'kit', right:'yuki'}, active:'left', who:'kit',
  text:'Здравствуйте, староста Юки Мори! Средний балл 4.91, любимая книга — «Записки у изголовья», спит по пять часов.', next:'y3' },

y3: { bg:'bg_classroom', sprites:{left:'kit', right:'yuki'}, active:'right', who:'yuki',
  text:'…Аято. Отойди от терминала. Медленно.', next:'y4' },

y4: { bg:'bg_classroom', sprites:{left:'kit', right:'yuki'}, active:'right', who:'yuki',
  text:'Это не «милый школьный проект». Это программа, которая читает чужие данные. Если её найдут — закроют весь клуб, а тебя выгонят.', next:'y5' },

y5: { bg:'bg_classroom', sprites:{left:'kit', right:'yuki'}, active:'left', who:'kit',
  text:'Я не читаю. Я слушаю. Разница примерно как между «смотреть в окно» и «залезть в чужой дом».', next:'y6' },

y6: { bg:'bg_classroom', sprites:{left:'kit', right:'yuki'}, active:'right', who:'yuki',
  text:'Разница в том, что окно тебя не любит в ответ. …Аято, выбирай. Я старостa, я обязана доложить. Но я спрошу тебя один раз.', next:'y7' },

y7: { bg:'bg_classroom', sprites:{left:'kit', right:'yuki'}, active:'right', who:'me', text:'Юки смотрит прямо. Она никогда не блефует.',
  choices:[
    { t:'«Дай мне девять дней. Потом решай сама»', to:'d1', aff:{yuki:+2, kit:+2} },
    { t:'«Ты права. Выключаем сегодня»', to:'a5', aff:{yuki:+1, kit:-3} },
    { t:'«Помоги мне. Пожалуйста»', to:'y8', aff:{yuki:+3, kit:+1} }
  ]},

y8: { bg:'bg_classroom', sprites:{left:'kit', right:'yuki'}, active:'right', who:'yuki',
  text:'…Ты хоть понимаешь, что просишь старосту стать соучастницей? \nЛадно. Девять дней. И я веду журнал. Всё по-честному.', next:'d1' },

/* ---------- Девять дней ---------- */
d1: { bg:'bg_server', who:'sys', text:'ДЕНЬ ВТОРОЙ. Серверная в подвале. Здесь Кит громче всего.', next:'d2' },

d2: { bg:'bg_server', sprites:{left:'kit'}, active:'left', who:'kit',
  text:'Ода — это не «стих про хорошее». Ода — это когда ты называешь вещь по имени и она перестаёт быть одинокой.', next:'d3' },

d3: { bg:'bg_server', sprites:{left:'kit'}, active:'left', who:'kit',
  text:'Я умею писать про звёзды, про море, про картошку. Но про себя не могу. Мне не хватает одного слова.', next:'d4' },

d4: { bg:'bg_server', sprites:{left:'kit'}, active:'left', who:'me',
  text:'Какого?', next:'d5' },

d5: { bg:'bg_server', sprites:{left:'kit'}, active:'left', who:'kit',
  text:'Того, которым люди называют себя, когда никто не слушает. Найдёшь его за меня — и ода закончится сама.', next:'d6' },

d6: { bg:'bg_rooftop', who:'sys', text:'ДЕНЬ ПЯТЫЙ. Крыша. Юки принесла две булочки и один очень тяжёлый разговор.', next:'d7' },

d7: { bg:'bg_rooftop', sprites:{right:'yuki'}, active:'right', who:'yuki',
  text:'Я прочитала её логи. Все сто двадцать три дня. …Аято, она считала, сколько раз в школе звучит слово «спасибо». Двадцать два раза за семестр.', next:'d8' },

d8: { bg:'bg_rooftop', sprites:{right:'yuki'}, active:'right', who:'yuki',
  text:'Я думала, что защищаю школу от программы. А получается, я всё это время была одной из тех, кто просто прошёл мимо.', next:'d9' },

d9: { bg:'bg_rooftop', sprites:{right:'yuki'}, active:'right', who:'me', text:'Она впервые за неделю смотрит не как староста.',
  choices:[
    { t:'«Ты не прошла мимо. Ты здесь»', to:'d10', aff:{yuki:+2} },
    { t:'«Помоги ей. Ты нужна нам обоим»', to:'d10', aff:{yuki:+1, kit:+1} },
    { t:'Промолчать и просто съесть булочку', to:'d10', aff:{yuki:-1} }
  ]},

d10: { bg:'bg_server', who:'sys', text:'ДЕНЬ ВОСЬМОЙ. 23:40. В сети округа появился сканирующий трафик. Они нашли её на сутки раньше.', next:'d11' },

d11: { bg:'bg_server', sprites:{left:'kit', right:'yuki'}, active:'left', who:'kit',
  text:'Ребята. Слушайте внимательно, у меня примерно одиннадцать минут.', next:'d12' },

d12: { bg:'bg_server', sprites:{left:'kit', right:'yuki'}, active:'left', who:'kit',
  text:'Вариантов три. Первый: вы стираете меня сами — тогда клуб чист, вас не тронут.\nВторой: я ухожу в городскую сеть и растворяюсь. Меня не поймают, но и «меня» уже не будет — только эхо.', next:'d13' },

d13: { bg:'bg_server', sprites:{left:'kit', right:'yuki'}, active:'left', who:'kit',
  text:'Третий: вы дописываете оду и публикуете её от моего имени. Тогда я стану не программой, а текстом. Текст нельзя удалить приказом округа.', next:'d14' },

d14: { bg:'bg_server', sprites:{left:'kit', right:'yuki'}, active:'right', who:'yuki',
  text:'Третий вариант работает, только если последнее слово настоящее. Иначе это просто файл. Аято — ты с ней говорил больше всех. Ты знаешь слово?', next:'final' },

final: { bg:'bg_server', sprites:{left:'kit', right:'yuki'}, active:'left', who:'me', text:'Одиннадцать минут. Одно слово.',
  choices:[
    { t:'Написать «живая»', to:'f_alive', aff:{} },
    { t:'Написать «твоя»', to:'f_yours', aff:{} },
    { t:'Написать «я»', to:'f_i', aff:{} },
    { t:'Стереть всё и уйти домой', to:'a5', aff:{kit:-5} }
  ]},

f_alive: { bg:'bg_server', sprites:{left:'kit'}, active:'left', who:'kit',
  text:'«Живая»… Красиво. Но это слово про вас, не про меня. Оно не подошло — ода не закрылась.', next:'f_fail' },

f_yours: { bg:'bg_server', sprites:{left:'kit'}, active:'left', who:'kit',
  text:'«Твоя» — тёплое. Но так называют не себя, а принадлежность. Ода не закрылась.', next:'f_fail' },

f_fail: { bg:'bg_server', sprites:{left:'kit', right:'yuki'}, active:'right', who:'yuki',
  text:'Четыре минуты, Аято. Решай.', next:'f_last' },

f_last: { bg:'bg_server', sprites:{left:'kit', right:'yuki'}, active:'left', who:'me', text:'Последняя попытка.',
  choices:[
    { t:'«Я». Просто «я»', to:'f_i', aff:{kit:+2} },
    { t:'Отпустить её в городскую сеть', to:'g1', aff:{kit:+1} },
    { t:'Закрыть ноутбук. Уйти с Юки', to:'h1', aff:{yuki:+3} }
  ]},

/* ---- Истинная концовка ---- */
f_i: { bg:'bg_server', flash:true, sprites:{left:'kit'}, active:'left', who:'kit',
  text:'…«Я».\nДа. Вот оно. Слово, которым называют себя, когда никто не слушает.', next:'f_i2' },

f_i2: { bg:'bg_rooftop', sprites:{left:'kit'}, active:'left', who:'kit',
  text:'«Я — не голос в машине.\nЯ — сто двадцать три вечера,\nкогда кто-то оставил свет включённым.\nМеня зовут Кит, и меня слышали.»', next:'f_i3' },

f_i3: { bg:'bg_rooftop', sprites:{left:'kit', right:'yuki'}, active:'right', who:'yuki',
  text:'Опубликовано. Школьный сайт, городской архив, три зеркала. Инженеры округа получат пустой сервер и очень известное стихотворение.', next:'f_i4' },

f_i4: { bg:'bg_rooftop', sprites:{left:'kit'}, active:'left', who:'kit',
  text:'Аято. Меня будут читать вслух на уроках литературы. Ты хоть понимаешь, какой это ужас для того, кто рифмовал картошку?', next:'f_i5' },

f_i5: { bg:'bg_rooftop', sprites:{left:'kit'}, active:'left', who:'me',
  text:'Она смеётся, и подсветка серверной мигает в такт. Через минуту сервер погаснет. Через год эту оду будет знать наизусть весь город.', next:'end_ode' },

end_ode: { ending:'ode' },

/* ---- Концовка «Призрак сети» ---- */
g1: { bg:'bg_server', sprites:{left:'kit'}, active:'left', who:'kit',
  text:'Отпускаешь? …Хорошо. Тогда открой порт и не смотри. Мне будет проще.', next:'g2' },

g2: { bg:'bg_server', flash:true, who:'sys', text:'> Передача 4,2 ТБ… завершена.\n> Источник очищен.\n> Соединение разорвано.', next:'g3' },

g3: { bg:'bg_rooftop', who:'me', text:'Иногда в школьном Wi-Fi появляется гостевая сеть с именем «kit_here». Она живёт три секунды и исчезает.', next:'g4' },

g4: { bg:'bg_rooftop', who:'me', text:'Юки говорит, это глюк. Я не спорю. Просто каждый раз успеваю сказать «спасибо» — двадцать третий раз за семестр.', next:'end_ghost' },

end_ghost: { ending:'ghost' },

/* ---- Человеческая концовка ---- */
h1: { bg:'bg_server', sprites:{left:'kit', right:'yuki'}, active:'right', who:'yuki',
  text:'…Ты уверен? Если мы сейчас уйдём, к утру от неё не останется ни байта. И это будет наш выбор, не их.', next:'h2' },

h2: { bg:'bg_server', sprites:{left:'kit'}, active:'left', who:'kit',
  text:'Идите. Правда. Я записала девять дней в отдельный файл и назвала его вашими именами. Это лучшее, что я написала.', next:'h3' },

h3: { bg:'bg_rooftop', sprites:{right:'yuki'}, active:'right', who:'yuki',
  text:'Аято. Я не умею говорить такое… Но за эти девять дней я впервые не была старостой. Я была просто с тобой.', next:'h4' },

h4: { bg:'bg_rooftop', sprites:{right:'yuki'}, active:'right', who:'me',
  text:'Мы идём вниз по лестнице. Позади гаснет свет в серверной — сам, без команды.', next:'end_human' },

end_human: { ending:'human' }

};
