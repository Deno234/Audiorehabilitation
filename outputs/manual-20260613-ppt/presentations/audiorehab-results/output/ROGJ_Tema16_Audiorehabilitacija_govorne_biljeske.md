# Govorne bilješke za prezentaciju

Trajanje: ciljaj 12-14 minuta i ostavi 1-2 minute za pitanja. Govori mirno; gotovo svaka slajd ima jednu glavnu poruku.

## Slajd 1 — Naslov

Reci: Tema je evaluacija jezičnih generativnih modela za audiorehabilitaciju. Cilj nije samo generirati lijepe riječi, nego provjeriti mogu li se dobiti hrvatske riječi i kratke rečenice s kontroliranim fonemskim sastavom, a zatim ih pretvoriti u audio.

## Slajd 2 — Motivacija

Objasni problem: u audiorehabilitaciji trebamo materijal koji cilja određene glasove ili kontraste. Ako korisnik ima problem razlikovati /s/ i /š/, nije dovoljno imati bilo koju rečenicu. Treba znati koji fonemi se stvarno pojavljuju i u kojem omjeru.

## Slajd 3 — Istraživačko pitanje

Glavna ideja: LLM može biti koristan kao generator kandidata, ali nije pouzdan evaluator. Zato je doprinos rada reproducibilni Python pipeline koji sve broji i provjerava deterministički.

Ako profesor pita „zašto ne vjerovati ChatGPT-u?”: Zato što LLM često daje uvjerljiv odgovor, ali nema garantirano točno brojanje fonema, pogotovo za hrvatske višeslovne foneme dž, lj i nj.

## Slajd 4 — Veza s literaturom

Reci da se oslanjamo na rad Andrijašević i Vukelić, gdje se GPT koristi za generiranje hrvatskog govornog materijala za auditivni trening. Mi preuzimamo ideju pet klasa fonema i razina zasićenja, ali uvodimo strožu validaciju.

Važno: HJP u promptu je samo uputa modelu. U našem radu HJP valjanost je zasebna ručna provjera riječi.

## Slajd 5 — Fonemske klase i formula

Objasni formulu: broj fonema ciljne klase dijeli se s ukupnim brojem fonema i množi sa 100. Ako ciljamo klasu N na 70 %, kandidat prolazi samo ako barem 70 % njegovih fonema pripada klasi N.

Tehnički detalj: parser ide longest-match-first za dž, lj i nj. Bez toga bi npr. „panj” pogrešno postao p-a-n-j umjesto p-a-nj.

## Slajd 6 — Pipeline

Objasni što skripta radi:

1. Učita CSV ili generira kandidate preko Ollame.
2. Normalizira tekst u UTF-8, čuva hrvatske znakove.
3. Fonemizira tekst.
4. Računa zasićenje.
5. Provjerava dopuštene znakove, broj riječi, duplikate i ponovljene riječi.
6. Dodaje Hunspell screening i ručni HJP word-review.
7. Stvara CSV i Markdown izvještaje.

Ako pita „koje su glavne datoteke”: `src/phonemizer.py`, `src/validators.py`, `src/metrics.py`, `src/pipeline.py`, `src/tts.py`, `src/asr_eval.py`.

## Slajd 7 — Dizajn eksperimenata

Reci da postoje tri sloja:

Prvi je reprodukcija paper-style promptova. Drugi je Task 16 usporedba ChatGPT Plus protiv lokalne Ollame. Treći je audio faza samo na validiranim kandidatima.

Naglasak: audio ne radimo nad svim kandidatima, nego samo nad onima koji su prošli determinističku i leksičku provjeru.

## Slajd 8 — Reprodukcija rada

Glavna poruka: kod rečenica se vidi očekivani pad na 70 % zasićenja. To se slaže s intuicijom iz rada: što je zasićenje više, model ima manje slobode i lakše proizvodi čudne ili nevaljane kandidate.

Kod riječi rezultati nisu savršeno monotoni jer duplikati jako utječu na tehničku valjanost. To je važan nalaz: model može pogoditi foneme, ali ponavljati iste riječi.

## Slajd 9 — ChatGPT Plus vs Ollama

Ovo je najvažniji tekstni rezultat. ChatGPT Plus ima 48,6 % tehnički valjanih kandidata i 85,9 % saturation pass. Ollama ima samo 4,5 % tehnički valjanih i 4,6 % saturation pass.

Zaključak: u ovoj konfiguraciji lokalni `llama3.1:8b` nije dovoljan za strogo hrvatsko fonemsko zasićenje. ChatGPT Plus je znatno bolji generator, ali i dalje treba validaciju.

## Slajd 10 — Analiza grešaka

Objasni razliku u vrstama grešaka:

ChatGPT Plus: najveći problem su duplikati. To znači da model često razumije zadatak, ali se vrti oko istih sigurnih kandidata.

Ollama: najveći problem je sam fonetski kriterij. To je ozbiljniji problem jer znači da generirani tekst ne zadovoljava glavnu znanstvenu mjeru.

## Slajd 11 — Hunspell i HJP

Reci da Hunspell nije HJP. Hunspell je automatski screening: može odbaciti valjane flektirane riječi ili prihvatiti riječ koja nije prikladna za rehabilitacijski kontekst.

Ručni HJP word-review: iz kandidata se izvezu jedinstvene riječi, označi se `hjp_valid`, a zatim se ta odluka propagira natrag na riječi i rečenice. Rečenica je HJP-valid samo ako su sve njezine riječi HJP-valid.

## Slajd 12 — Audio dizajn

Objasni da je za poštenu TTS usporedbu isti skup od 96 tekstova poslan u sva tri sustava: eSpeak NG, Coqui VITS HR i SpeechT5 HR. Time se ne uspoređuju različiti tekstovi, nego različiti sintetizatori na istom materijalu.

Svi izlazi su normalizirani u isti format: WAV, mono, 16 kHz, 16-bit PCM.

## Slajd 13 — TTS i ASR

Sva tri TTS sustava tehnički su uspjela sintetizirati 96/96 kandidata. ASR evaluacija koristi fiksni `faster-whisper large-v3-turbo` profil za hrvatski.

Reci caveat: WER/CER nije klinički dokaz. To je automatski proxy. Visok WER može značiti da je TTS loš, ASR loš, ili da je materijal fonemski neobičan.

## Slajd 14 — Audio demo

Ovdje pusti tri WAV datoteke istim redom: eSpeak NG, Coqui VITS HR, SpeechT5 HR. Naglasi da je tekst isti: „Draga rada radi.” Time se sluša razlika u sintetizatoru, a ne razlika u sadržaju.

Reci da su demo kopije pojačane za prezentaciju jer je SpeechT5 u originalnom izlazu bio tiši. Originalni istraživački audio nije mijenjan; pojačanje je samo praktično za slušanje u učionici.

## Slajd 15 — Slušna provjera

Ovo je važan ljudski rezultat. eSpeak NG je najrazumljiviji po ljudskoj ocjeni, iako nije najprirodniji. SpeechT5 je najprirodniji, ali ne najrazumljiviji. Coqui je u ovom testu najslabiji.

Poanta: automatska ASR metrika i ljudska procjena ne moraju dati isti poredak, zato se ne smije stati samo na WER/CER.

## Slajd 16 — Zaključak

Zaključi:

1. Pipeline radi i reproducibilan je.
2. LLM može pomoći u generiranju kandidata, ali samo ako Python deterministički validira.
3. ChatGPT Plus je bio bolji od lokalne Ollame za tekst.
4. Audio faza je tehnički izvediva, ali klinička prikladnost traži stručnu provjeru.

## Kratki odgovori ako profesor pita

**Kako fonemizator radi?**  
Tekst se pretvara u mala slova, uklanja se interpunkcija, čuvaju se hrvatski znakovi, a `dž`, `lj` i `nj` se prepoznaju prije pojedinačnih slova. Razmaci ne ulaze u broj fonema.

**Što znači saturation pass?**  
Ako kandidat ima N fonema, a nk pripada ciljnoj klasi, zasićenje je nk/N × 100. Kandidat prolazi ako je postotak veći ili jednak traženom pragu.

**Zašto imate Hunspell i HJP?**  
Hunspell je automatski i skalabilan, ali nije konačan. HJP/manual word-review je bliže kriteriju iz literature, ali je ručni.

**Zašto je Ollama tako slaba?**  
Testirani lokalni model nije pouzdano pratio hrvatske fonemske klase. Većina kandidata pala je na zasićenju, ne samo na hrvatskoj leksici.

**Zašto TTS nije klinički zaključak?**  
Jer tehnički WAV i dobra ASR transkripcija ne dokazuju da je izgovor terapeutski prikladan. Potrebni su stručnjaci, više slušatelja i eventualno korisničko testiranje.

**Što biste poboljšali?**  
Veći ručni listening review, više ocjenjivača, inter-rater reliability, jači lokalni LLM, repair loop za neuspjele kandidate i formalniji HJP/klinički review.
