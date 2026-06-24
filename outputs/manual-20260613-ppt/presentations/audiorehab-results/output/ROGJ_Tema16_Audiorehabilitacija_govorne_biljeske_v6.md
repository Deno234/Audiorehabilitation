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

## Slajd 7 — Tehnička implementacija

Ovdje pokaži da je rad računalni sustav, ne samo promptanje. Ukratko prođi module.

`phonemizer.py` normalizira tekst i pretvara ga u foneme. `phoneme_classes.py` zna kojoj klasi pripada svaki fonem. `validators.py` računa saturation i dodaje failure reasons. `metrics.py` računa PCD, frekvencije i duplicate rate. `generators.py` služi za ručni CSV i Ollama generiranje. `pipeline.py` sve povezuje preko CLI naredbi. `tts.py` i `asr_eval.py` rade audio fazu.

Naglasak: svi rezultati su CSV/Markdown, UTF-8, s `run_id`, tako da je eksperiment ponovljiv.

## Slajd 8 — Algoritam

Objasni algoritam jednostavno: prvo normalizacija teksta, zatim parsiranje fonema. Najvažnije je longest-match-first za `dž`, `lj`, `nj`, jer su to jedan fonem, a ne dva slova.

Nakon toga se izračuna saturation: broj fonema ciljne klase podijeljen s ukupnim brojem fonema. Ako je prag 70 %, kandidat s 65 % pada, bez obzira na to koliko lijepo izgleda.

Failure reasons su bitni jer kandidat može pasti iz više razloga. Na primjer, rečenica može istovremeno imati premalo zasićenje i pogrešan broj riječi.

## Slajd 9 — Dizajn eksperimenata

Reci da postoje tri sloja:

Prvi je reprodukcija paper-style promptova. Drugi je Task 16 usporedba ChatGPT Plus protiv lokalne Ollame. Treći je audio faza samo na validiranim kandidatima.

Naglasak: audio ne radimo nad svim kandidatima, nego samo nad onima koji su prošli determinističku i leksičku provjeru.

## Slajd 10 — Reprodukcija rada: riječi

Ovdje reci da je ovo namjerno prikazano gotovo istim formatom kao Table II u radu. U paperu su retci fonemske klase, stupci su saturation leveli, a ćelija je postotak riječi koje zadovoljavaju oba kriterija: zasićenje + standardni hrvatski/HJP.

Naša tablica koristi isti princip: saturation pass + ručni HJP word-review. Važno je reći da naš pipeline dodatno mjeri duplikate, ali ih ovdje ne miješamo u ćeliju jer želimo metodološki isti indikator kao u paperu.

Zaključak za riječi: naši paper-style rezultati su vrlo visoki za većinu klasa, ali SV na 70 % i V na 80 % pokazuju pad. To je usporedivo s idejom rada da visoka zasićenja i “visoke” klase postaju teže.

## Slajd 11 — Reprodukcija rada: rečenice

Ovdje je analog Table III iz rada. Paper za rečenice prikazuje postotak rečenica koje zadovoljavaju saturation level. Mi prikazujemo isti kriterij.

Glavna poruka: na 50 % smo gotovo savršeni za većinu klasa. Na 70 % se vidi pad, posebno za klasu V. To je važan zaključak jer se slaže s očekivanjem: viši prag daje modelu manje slobode.

## Slajd 12 — ChatGPT Plus vs Ollama

Ovo je najvažniji tekstni rezultat. ChatGPT Plus ima 48,6 % tehnički valjanih kandidata i 85,9 % saturation pass. Ollama ima samo 4,5 % tehnički valjanih i 4,6 % saturation pass.

Zaključak: u ovoj konfiguraciji lokalni `llama3.1:8b` nije dovoljan za strogo hrvatsko fonemsko zasićenje. ChatGPT Plus je znatno bolji generator, ali i dalje treba validaciju.

## Slajd 13 — Analiza grešaka

Objasni razliku u vrstama grešaka:

ChatGPT Plus: najveći problem su duplikati. To znači da model često razumije zadatak, ali se vrti oko istih sigurnih kandidata.

Ollama: najveći problem je sam fonetski kriterij. To je ozbiljniji problem jer znači da generirani tekst ne zadovoljava glavnu znanstvenu mjeru.

## Slajd 14 — Tehnička valjanost i PCD

Ovo je slajd za metodološko objašnjenje. Reci da `is_valid` nije procjena LLM-a, nego rezultat determinističkih pravila.

Kandidat je tehnički valjan ako prođe sve ove pragove: zasićenje mora biti veće ili jednako traženom SL-u, znakovi smiju biti samo hrvatska slova i razmaci, riječ mora imati točno jednu riječ, rečenica mora imati 3 do 5 riječi, kandidat ne smije biti duplikat u istom runu i rečenica ne smije ponavljati istu riječ.

U eksperimentima su pragovi bili: za paper riječi 40, 50, 60, 70 i 80 %, za paper rečenice 50 i 70 %, a za Task 16 usporedbu 50 i 70 %. Dakle `saturation_level` nije procjena, nego konkretan numerički prag u CSV-u.

PCD znači Phonetic Content Dissimilarity. Naš paper-style PCD uspoređuje fonemski sadržaj dvaju kandidata: gleda koliko fonema u duljem kandidatu nije dijeljeno s kraćim, podijeljeno duljinom duljeg kandidata. Veći prosječni PCD znači raznolikiji skup.

Rezultat: ChatGPT Plus ima viši prosječni PCD po grupama od Ollame, što znači da je osim više validnih kandidata dao i korisniju fonetsku raznolikost. Ollama ima malo grupa s dovoljno validnih kandidata, pa je i PCD slabiji.

## Slajd 15 — Hunspell i HJP

Reci da Hunspell nije HJP. Hunspell je automatski spelling/dictionary screening: pipeline uzima normalizirane riječi i šalje ih lokalnom alatu `hunspell -d hr_HR -l`. Ako Hunspell vrati riječ kao nepoznatu, kandidat dobiva `dictionary_failed`, a u CSV-u se sprema `dictionary_invalid_words`.

Važno: Hunspell radi riječ-po-riječ. On ne zna je li rečenica semantički prirodna, klinički prikladna ili stvarno potvrđena na HJP-u. Može odbaciti valjani flektirani oblik, a može i prihvatiti riječ koja nije dobra za rehabilitacijski materijal.

Ručni HJP word-review: iz kandidata se izvezu jedinstvene riječi, označi se `hjp_valid`, a zatim se ta odluka propagira natrag na riječi i rečenice. Rečenica je HJP-valid samo ako su sve njezine riječi HJP-valid.

## Slajd 16 — Što utječe na rezultate

Ovaj slajd služi da ne pomiješamo različite razine validacije.

Prvo je `SL prolaznost`: to je samo fonetski kriterij. Ako kandidat nema dovoljno fonema ciljne klase, pada bez obzira na to je li riječ hrvatska.

Drugo je `tehnička valjanost`: u normalnoj tekstnoj usporedbi to znači saturation pass, dopušteni znakovi, ispravan broj riječi, bez duplikata i bez ponavljanja riječi. To je osnovni Python pass/fail.

Treće je Hunspell: to je automatski leksički screening. On utječe na Hunspell valid rate i technical + Hunspell valid rate. Ne smije se interpretirati kao HJP dokaz.

Četvrto je HJP/manual valid: to je ručni word-level review. Za riječ je dovoljno da je ta riječ yes. Za rečenicu sve riječi moraju biti yes. Ovo je najbliže kriteriju iz paper-a o standardnom hrvatskom jeziku.

PCD ne odlučuje valjanost. On samo govori koliko su kandidati fonetski raznoliki. TTS success govori samo je li audio tehnički napravljen. WER/CER i slušanje govore o audio razumljivosti, ali nisu kliničko odobrenje.

## Slajd 17 — Audio dizajn

Objasni da je za poštenu TTS usporedbu isti skup od 96 tekstova poslan u sva tri sustava: eSpeak NG, Coqui VITS HR i SpeechT5 HR. Time se ne uspoređuju različiti tekstovi, nego različiti sintetizatori na istom materijalu.

Svi izlazi su normalizirani u isti format: WAV, mono, 16 kHz, 16-bit PCM.

## Slajd 18 — TTS i ASR

Sva tri TTS sustava tehnički su uspjela sintetizirati 96/96 kandidata. ASR evaluacija koristi fiksni `faster-whisper large-v3-turbo` profil za hrvatski.

Reci caveat: WER/CER nije klinički dokaz. To je automatski proxy. Visok WER može značiti da je TTS loš, ASR loš, ili da je materijal fonemski neobičan.

## Slajd 19 — Audio demo

Ovdje pusti tri WAV datoteke istim redom: eSpeak NG, Coqui VITS HR, SpeechT5 HR. Naglasi da je tekst isti: „Draga rada radi.” Time se sluša razlika u sintetizatoru, a ne razlika u sadržaju.

Reci da su demo kopije pojačane za prezentaciju jer je SpeechT5 u originalnom izlazu bio tiši. Originalni istraživački audio nije mijenjan; pojačanje je samo praktično za slušanje u učionici.

## Slajd 20 — Slušna provjera

Ovo je važan ljudski rezultat. eSpeak NG je najrazumljiviji po ljudskoj ocjeni, iako nije najprirodniji. SpeechT5 je najprirodniji, ali ne najrazumljiviji. Coqui je u ovom testu najslabiji.

Poanta: automatska ASR metrika i ljudska procjena ne moraju dati isti poredak, zato se ne smije stati samo na WER/CER.

## Slajd 21 — Zaključak

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
