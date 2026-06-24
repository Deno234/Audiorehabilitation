# Detaljne govorne bilješke za prezentaciju

Prezentacija: `ROGJ_Tema16_Audiorehabilitacija_rezultati_v6.pptx`  
Jezik izlaganja: hrvatski  
Ciljano trajanje: 12-15 minuta

## Kako tempirati izlaganje

Ako imaš maksimalno 15 minuta, nemoj jednako dugo govoriti o svakom slajdu. Uvodne slajdove prođi brzo, a najviše vremena daj metodologiji, validaciji i rezultatima.

- Slajdovi 1-4: oko 2 minute ukupno
- Slajdovi 5-8: oko 3 minute, tehnička jezgra
- Slajdovi 9-16: oko 6 minuta, tekstni rezultati i evaluacija
- Slajdovi 17-21: oko 4 minute, audio, demo i zaključak

Glavna rečenica koju stalno možeš ponavljati:

> LLM u ovom radu nije evaluator, nego samo generator kandidata. Sve odluke o valjanosti donosi deterministički Python pipeline.

## Slajd 1 — Naslov

Reci:

“Tema rada je evaluacija jezičnih generativnih modela za potrebe audiorehabilitacije. Konkretno, istražujem mogu li modeli generirati hrvatske riječi i kratke hrvatske rečenice koje su fonetski kontrolirane, odnosno imaju dovoljno fonema iz ciljane fonemske klase. Nakon toga validirani tekst pretvaram u govor i provjeravam kvalitetu audio zapisa.”

Naglasak:

Ovo nije samo promptanje ChatGPT-a. Cilj je reproducibilan računalni postupak: generiranje, fonemizacija, validacija, metrika, izvještaj i audio evaluacija.

## Slajd 2 — Motivacija

Reci:

“U audiorehabilitaciji se često trebaju vježbati specifični glasovi ili kontrasti. Ako osoba teže razlikuje, primjerice, /s/ i /š/, nije dovoljno dati bilo koju hrvatsku rečenicu. Treba znati koji se fonemi pojavljuju i koliko često. Zato uvodim kontrolu fonemskog sadržaja.”

Objasni tri koraka:

1. Imamo slušni problem ili ciljanu fonemsku skupinu.
2. Trebamo tekst koji zasićuje tu skupinu.
3. Tek nakon validacije tekst se može sintetizirati u audio vježbu.

Ako profesor pita “zašto LLM?”:

“LLM je koristan za brzo predlaganje kandidata, ali nije pouzdan za provjeru fonema. Zato sam ga koristio samo kao generator.”

## Slajd 3 — Istraživačko pitanje i doprinos

Reci:

“Glavno istraživačko pitanje je: mogu li LLM-ovi generirati hrvatske riječi i rečenice koje zadovoljavaju stroge fonemske kriterije, i može li se validirani tekst pretvoriti u tehnički ispravan i razumljiv audio?”

Zatim objasni četiri doprinosa:

- evaluacija generiranja hrvatskog teksta pod fonemskim ograničenjima
- deterministički Python validator
- usporedba ChatGPT Plus i lokalne Ollame
- proširenje na TTS, ASR i slušnu provjeru

Važna obrambena rečenica:

“Namjerno ne vjerujem modelu kad kaže da je nešto točno. Model može dati uvjerljiv odgovor, ali Python ponovno broji foneme i odlučuje prolazi li kandidat.”

## Slajd 4 — Veza s radom Andrijašević i Vukelić

Reci:

“Rad koji reproduciram koristi GPT-4 za generiranje govornog materijala za auditivni trening. Preuzimam pet fonemskih klasa, razine zasićenja i ideju generiranja riječi i kratkih rečenica. Moja glavna razlika je u tome što validaciju ne prepuštam LLM-u.”

Objasni:

- paper koristi promptove i ručnu provjeru
- moj rad dodaje deterministički parser i CSV/Markdown pipeline
- HJP u promptu je samo zahtjev modelu, ne dokaz

Ako pita “što je metodološki isto?”:

“Metodološki isto je da gledam iste fonemske klase i zasićenja, te prikazujem rezultate po klasama i saturation levelima kao u njihovim tablicama.”

## Slajd 5 — Fonemske klase i formula

Reci:

“Koristim pet fonemskih klasa: N, SN, S, SV i V. Svaka klasa ima popis fonema. Kandidat se fonemizira, zatim se broji koliko fonema pripada ciljnoj klasi.”

Formula:

`zasićenje = broj fonema ciljne klase / ukupan broj fonema × 100`

Primjer:

“Ako kandidat ima 10 fonema, a 7 ih je iz ciljne klase, zasićenje je 70 %. Ako je prag 70 %, kandidat prolazi. Ako ima 6 od 10, pada.”

Tehnički detalj:

“Posebno sam morao paziti na hrvatske višeslovne foneme `dž`, `lj` i `nj`. Parser ih prepoznaje longest-match-first, tako da `panj` postaje `p, a, nj`, a ne `p, a, n, j`.”

## Slajd 6 — Implementirani postupak

Reci:

“Pipeline radi od ulaza do izvještaja. Ulaz može biti ručni CSV iz ChatGPT Plus odgovora ili automatska lokalna Ollama generacija. Nakon toga slijedi ista validacija.”

Objasni redom:

1. prompt definira klasu, zasićenje i tip teksta
2. LLM generira kandidate
3. fonemizator pretvara tekst u foneme
4. validator provjerava pragove
5. leksička provjera ide preko Hunspella i HJP word-reviewa
6. report generira CSV, Markdown i sažetke

Ako pita “što znači reproducibilno?”:

“Svaki eksperiment ima `run_id`, konfiguraciju, ulazni CSV, izlazne CSV datoteke i izvještaje. Tako se može provjeriti odakle dolazi svaka brojka.”

## Slajd 7 — Tehnička implementacija: moduli i podaci

Ovdje pokaži računalnu stranu rada.

Reci:

“Projekt je podijeljen na module. `phonemizer.py` radi hrvatsku fonemizaciju. `phoneme_classes.py` mapira foneme u klase. `validators.py` je najvažniji za pass/fail jer računa zasićenje i failure reasons. `metrics.py` računa PCD i distribucije. `generators.py` podržava ručni CSV i Ollamu. `pipeline.py` povezuje sve u CLI komande. `tts.py` i `asr_eval.py` rade audio dio.”

Naglasak za računarstvo:

- svi CSV fileovi su UTF-8
- nema ručnog brojanja fonema
- svaki kandidat dobiva strukturirani red s poljima: `phonemes`, `target_count`, `saturation_percentage`, `passes_saturation`, `is_valid`, `failure_reasons`

Ako profesor pita “gdje se donosi odluka?”:

“U `validators.py`, funkcija `validate_candidate`. Ona skuplja failure reasons; ako je lista prazna, `is_valid=True`, inače `False`.”

## Slajd 8 — Ključni algoritam: fonemizacija i validacija

Reci:

“Algoritam prvo normalizira tekst: mala slova, uklanjanje interpunkcije, očuvanje hrvatskih dijakritika. Nakon toga parsira foneme. Kod `dž`, `lj` i `nj` koristi longest-match-first.”

Zatim:

“Za saturation se broji koliko fonema pripada ciljnoj klasi. To je determinističko brojanje, nema LLM procjene.”

Failure reasons:

- `failed_saturation`: premalo fonema iz ciljne klase
- `invalid_characters`: strani znakovi, brojke ili nedopušteni simboli
- `wrong_word_count`: riječ nije jedna riječ ili rečenica nema 3-5 riječi
- `duplicate`: isti normalizirani kandidat već se pojavio
- `repeated_words`: ista riječ se ponavlja u rečenici
- `dictionary_failed`: Hunspell/manual dictionary sloj nije prošao

Važna rečenica:

“Kandidat može pasti iz više razloga istovremeno, zato čuvam sve failure reasons, a ne samo jedan pass/fail.”

## Slajd 9 — Dizajn eksperimenata

Reci:

“Imao sam tri razine eksperimenta. Prva je reprodukcija literature. Druga je puni Task 16 tekstni eksperiment, gdje uspoređujem ChatGPT Plus i Ollamu. Treća je audio faza, ali samo na kandidatima koji su prošli validaciju.”

Brojke:

- paper reproduction riječi: 275 kandidata
- paper reproduction rečenice: 210 kandidata
- Task 16: oko 800 kandidata po izvoru
- TTS-ready skup: 355 kandidata
- TTS podskup: 96 kandidata

Objasni zašto audio tek kasnije:

“Nema smisla sintetizirati audio iz nevaljanog teksta jer bi TTS evaluacija tada miješala tekstne i audio pogreške.”

## Slajd 10 — Reprodukcija rada: riječi

Reci:

“Ovo je tablica napravljena po uzoru na Table II iz rada. U paperu ćelija znači postotak riječi koje zadovoljavaju oba kriterija: saturation level i standardni hrvatski/HJP kriterij.”

Naša analogija:

“Kod nas ćelija znači saturation pass + ručni HJP word-review. Time je usporedba metodološki bliža paperu.”

Važna napomena:

“Naš pipeline dodatno mjeri duplikate, ali ih u ovoj tablici ne miješam u ćeliju jer paper Table II nije primarno tablica duplikata, nego kriterija zasićenja i jezične valjanosti.”

Zaključak:

“Naši paper-style rezultati su visoki za većinu klasa, ali SV na 70 % i V na 80 % pokazuju pad. To se uklapa u očekivanje da viša zasićenja i teže klase smanjuju uspješnost.”

## Slajd 11 — Reprodukcija rada: rečenice

Reci:

“Ovo je analog Table III iz rada. Paper za rečenice prikazuje saturation-level criterion satisfied, pa i mi prikazujemo istu vrstu kriterija.”

Naglasak:

- na 50 % rezultati su vrlo jaki
- na 70 % rezultati padaju
- klasa V pada najviše

Interpretacija:

“Što je prag viši, model ima manje slobode da napravi prirodnu rečenicu, pa se češće pojavljuju neobične konstrukcije ili nedovoljno zasićenje.”

## Slajd 12 — ChatGPT Plus vs Ollama

Reci:

“Ovo je glavna usporedba tekstnog generiranja. ChatGPT Plus ima 797 kandidata, tehnički valid rate 48,6 % i saturation pass 85,9 %. Ollama ima 757 kandidata, ali samo 4,5 % tehnički valjanih i 4,6 % saturation pass.”

Zaključak:

“ChatGPT Plus je puno bolji u ovoj konfiguraciji. Ollama `llama3.1:8b` nije pouzdano pratila hrvatske fonemske klase.”

Ako profesor pita “je li Ollama loša općenito?”:

“Ne tvrdim da je Ollama općenito loša. Tvrdim da ovaj lokalni model, s ovim promptovima i ovim strogim hrvatskim fonemskim kriterijima, nije bio dovoljno pouzdan.”

## Slajd 13 — Što je najčešće pošlo krivo?

Reci:

“Kod ChatGPT Plusa najveći problem nisu fonemi, nego duplikati. To znači da model često zna pogoditi traženi fonemski obrazac, ali se ponavlja.”

“Kod Ollame je problem drugačiji: većina kandidata pada na saturation kriteriju. To je ozbiljnije jer znači da ne zadovoljava osnovnu fonetsku mjeru.”

Brojke:

- ChatGPT Plus: `duplicate=361`, `failed_saturation=112`
- Ollama: `failed_saturation=722`, `wrong_word_count=195`

## Slajd 14 — Tehnička valjanost i PCD

Ovo je ključan metodološki slajd.

Reci:

“Tehnička valjanost znači da je kandidat prošao determinističke pragove. To nije isto što i HJP, semantika ili klinička prikladnost.”

Tehnički pragovi:

- `saturation_percentage >= saturation_level`
- dopušteni su samo hrvatski znakovi i razmaci
- `word` mora imati točno 1 riječ
- `sentence` mora imati 3-5 riječi
- kandidat ne smije biti duplikat u istom runu
- rečenica ne smije imati ponovljene riječi

PCD:

“PCD mjeri fonetsku raznolikost. Paper-style verzija uspoređuje dva kandidata i gleda koliko fonema duljeg kandidata nije podijeljeno s kraćim kandidatom. Veći PCD znači raznolikiji skup.”

Rezultat:

- ChatGPT Plus: prosječni PCD po grupama 0,398
- Ollama: prosječni PCD po grupama 0,274

Interpretacija:

“ChatGPT Plus nije samo dao više valjanih kandidata, nego i bolju fonetsku raznolikost među grupama koje su imale dovoljno valjanih kandidata.”

## Slajd 15 — Hunspell screening + ručni HJP

Ovo je dio koji treba jasno objasniti.

Reci:

“Hunspell i HJP nisu ista stvar. Hunspell je automatski rječnički/spellcheck screening. Pipeline uzima normalizirane riječi i šalje ih lokalnom alatu `hunspell -d hr_HR -l`. Ako Hunspell vrati riječ kao nepoznatu, kandidat dobiva `dictionary_failed`.”

Što Hunspell radi:

- radi lokalno, bez web scraping-a
- provjerava riječi pomoću hrvatskog rječnika `hr_HR`
- vraća yes/no/unsure na razini kandidata
- zapisuje `dictionary_invalid_words` i `dictionary_unknown_words`

Što Hunspell ne radi:

- nije dokaz da riječ postoji u HJP-u
- ne razumije značenje rečenice
- ne procjenjuje kliničku prikladnost
- može odbiti valjani flektirani oblik
- može prihvatiti riječ koja nije dobra za rehabilitacijski kontekst

HJP:

“HJP je ručni word-level review. Izvezem jedinstvene riječi, ručno označim `hjp_valid=yes/no/unsure`, a zatim se ta odluka vraća na kandidate.”

Pravila:

- ako je kandidat riječ, HJP-valid je ako je ta riječ `yes`
- ako je kandidat rečenica, HJP-valid je samo ako su sve riječi `yes`
- ako je barem jedna riječ `no`, cijela rečenica je HJP-invalid

Rezultat:

- ChatGPT Plus Hunspell-valid: 95,4 %
- HJP-valid nakon word-reviewa: 776 / 797
- HJP-invalid: 21
- TTS-ready: 355 kandidata

## Slajd 16 — Što točno utječe na rezultate?

Reci:

“Ovaj slajd je mapa metrika. U radu ne postoji jedna jedina valjanost. Svaka metrika odgovara na drugo pitanje.”

Objasni redom:

- `SL prolaznost`: je li kandidat fonetski pogodio traženo zasićenje?
- `Tehnička valjanost`: je li prošao fonetska i strukturna Python pravila?
- `Hunspell valid`: prolaze li riječi automatski hrvatski rječnik?
- `Technical + Hunspell`: prolazi li i tehničku validaciju i automatski leksički screening?
- `HJP/manual valid`: prolazi li ručnu provjeru standardnojezične valjanosti?
- `PCD`: koliko je skup fonetski raznolik?
- `TTS success`: je li audio tehnički generiran u ispravnom WAV formatu?
- `WER/CER + slušanje`: koliko je audio razumljiv automatski i ljudski?

Ključna interpretacija:

“Zato u rezultatima uvijek pazim što mjerim. Na primjer, kandidat može proći saturation, ali pasti kao duplikat. Može proći Hunspell, ali biti semantički čudan. Može imati tehnički ispravan WAV, ali zvučati loše.”

## Slajd 17 — Audio faza

Reci:

“Audio fazu radim samo nad validiranim kandidatima. Za poštenu usporedbu isti tekst ide u sva tri TTS sustava.”

TTS sustavi:

- eSpeak NG hrvatski glas
- Coqui VITS HR
- SpeechT5 HR lokalni model

Tehnička normalizacija:

- WAV
- mono
- 16 kHz
- 16-bit PCM

Ako profesor pita “zašto normalizacija?”:

“Da ASR i slušna evaluacija ne uspoređuju različite formate, nego sadržaj i kvalitetu sintetizatora.”

## Slajd 18 — TTS i ASR WER/CER

Reci:

“Sva tri TTS sustava uspješno su sintetizirala 96/96 kandidata i svi izlazi su format-compliant.”

ASR:

“Za automatsku provjeru koristio sam jedan fiksni ASR profil: faster-whisper large-v3-turbo za hrvatski. Važno je da je ASR profil isti za sve TTS sustave, da ne miješamo TTS usporedbu s ASR model comparison.”

Rezultati:

- Coqui: WER 1,187; CER 0,693
- eSpeak: WER 1,076; CER 0,443
- SpeechT5: WER 0,967; CER 0,438

Caveat:

“WER/CER je proxy. Loš WER može biti zbog TTS-a, ASR-a ili zato što su rečenice fonemski neobične.”

## Slajd 19 — Audio demo

Reci prije puštanja:

“Sada puštam istu rečenicu kroz tri TTS sustava: `Draga rada radi.` Važno je da je tekst isti, tako da slušamo razliku u sintetizatorima, a ne razliku u sadržaju.”

Redoslijed:

1. eSpeak NG
2. Coqui VITS HR
3. SpeechT5 HR

Napomena:

“Ove demo kopije su pojačane samo radi prezentacije. Originalni istraživački WAV-ovi nisu mijenjani.”

## Slajd 20 — Slušna provjera

Reci:

“Osim ASR-a napravio sam i ljudsku slušnu provjeru na uravnoteženom uzorku: 20 redaka po TTS modelu, ukupno 60.”

Rezultati:

- eSpeak NG: najbolja razumljivost, 4,65 / 5
- SpeechT5 HR: najbolja prirodnost, 3,60 / 5
- Coqui VITS HR: najslabiji u ovom materijalu

Interpretacija:

“ASR i ljudska ocjena se ne poklapaju savršeno. ASR malo više favorizira SpeechT5, ali čovjek je eSpeak ocijenio najrazumljivijim. Zato ASR nije dovoljan sam.”

## Slajd 21 — Zaključak

Zaključi ovako:

“Pipeline je uspješno izgrađen i reproducibilan. ChatGPT Plus je bio korisniji generator od lokalne Ollame za ovaj strogi hrvatski fonemski zadatak. Međutim, nijedan LLM nije dovoljan bez determinističke validacije. Nakon tekstne validacije, audio faza je tehnički izvediva, ali klinička prikladnost i konačna jezična kvaliteta i dalje traže ljudsku i stručnu procjenu.”

Završna rečenica:

“Najvažniji rezultat rada nije samo lista riječi i rečenica, nego pipeline koji sprječava da LLM sam sebi bude sudac.”

## Kratki odgovori na moguća pitanja

### Kako točno odlučuješ je li kandidat validan?

Kandidat je validan ako nema nijedan failure reason. Provjeravam saturation, dopuštene znakove, broj riječi, duplikate, ponovljene riječi i, u Hunspell konfiguraciji, dictionary status.

### Je li Hunspell isto što i HJP?

Ne. Hunspell je automatski lokalni spellchecker/rječnik. HJP je ručni word-level review. Hunspell je screening; HJP je bliži standardnojezičnom kriteriju iz paper-a.

### Zašto u nekim tablicama ne uključuješ duplikate?

Kad radim paper-style usporedbu, želim imitirati indikator iz paper-a. Zato za riječi gledam saturation + HJP, a duplikate prikazujem kao zasebnu metriku u našem pipelineu.

### Zašto je ChatGPT bolji od Ollame?

U ovom eksperimentu ChatGPT Plus puno češće pogađa saturation kriterij. Ollama najčešće generira hrvatski izgledan tekst, ali fonemski ne zadovoljava traženu klasu i prag.

### Zašto audio nije klinički dokaz?

Zato što tehnički WAV, ASR transkripcija i jedna slušna ocjena ne znače da je materijal prikladan za terapiju. Za to trebaju stručnjaci i veći listening study.

### Koji je najvažniji računalni dio?

Deterministički validator: LLM generira kandidate, ali Python odlučuje. To uključuje hrvatski fonemizator, mapiranje u klase, saturation formulu, failure reasons i reproducibilne CSV izvještaje.
