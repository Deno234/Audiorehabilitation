# FULL govorne bilješke za obranu/prezentaciju

Prezentacija: `ROGJ_Tema16_Audiorehabilitacija_rezultati_v6.pptx`  
Tema: Evaluacija jezičnih generativnih modela za potrebe audiorehabilitacije  
Jezik: hrvatski  
Cilj: imati spremno i kratko izlaganje, ali i dovoljno tehničkih detalja za pitanja.

## Najvažnija ideja cijelog rada

Ovo nije rad u kojem se samo pita ChatGPT da generira riječi.

Glavna ideja je:

> LLM je generator kandidata, ali Python je evaluator.

Drugim riječima:

- ChatGPT Plus ili Ollama daju prijedloge riječi/rečenica.
- Python deterministički fonemizira tekst.
- Python broji foneme i računa zasićenje.
- Python detektira tehničke greške.
- Hunspell i HJP su dodatni leksički slojevi.
- TTS i ASR dolaze tek nakon tekstne validacije.

Ako te profesor pita “što je računalni doprinos?”, reci:

> Računalni doprinos je reproducibilni pipeline: ulazni CSV/promptovi, deterministički hrvatski fonemizator, validacijski kriteriji, failure reasons, PCD metrika, izvještaji, TTS manifesti i audio evaluacija.

## Kratki tempo za 15 minuta

Ima 21 slajd, ali ne moraš na svakom stajati jednako dugo.

- Slajdovi 1-4: brzo, kontekst i literatura.
- Slajdovi 5-8: tehnička jezgra, ovdje pokaži da je računarstvo.
- Slajdovi 9-16: tekstni eksperimenti, tablice i validacija.
- Slajdovi 17-21: audio, ASR, slušanje, zaključak.

Ako kasniš, preskoči detaljno čitanje slajdova 10 i 11; samo reci zaključak tablica.

---

# Slajd 1 — Naslov

## Što reći

“Tema mog rada je evaluacija jezičnih generativnih modela za potrebe audiorehabilitacije. Istražujem mogu li modeli generirati hrvatske riječi i kratke rečenice koje imaju kontrolirani fonemski sastav, odnosno zadani postotak fonema iz ciljane fonemske klase. Nakon tekstne validacije, dio kandidata pretvaram u audio i uspoređujem TTS sustave.”

## Što slajd dokazuje

Ovaj slajd uvodi cijeli tok:

LLM → fonemi → validacija → TTS → audio vježbe

## Dodatno pojašnjenje

Audiorehabilitacijski materijal ne smije biti bilo kakav tekst. Mora biti ciljano napravljen da sadrži određene glasove/foneme. Zato generativni model sam po sebi nije dovoljan; treba automatska i provjerljiva kontrola.

## Ako pitaju

**Zašto “evaluacija modela”, a ne samo “generiranje materijala”?**  
Zato što ne želim samo dobiti tekst, nego izmjeriti koliko dobro različiti izvori generiranja zadovoljavaju stroge kriterije.

---

# Slajd 2 — Motivacija

## Što reći

“U audiorehabilitaciji se često radi s ciljanim fonemima ili kontrastima. Ako netko teško razlikuje /s/ i /š/, nije dovoljno dati proizvoljnu rečenicu. Treba znati pojavljuju li se ciljani fonemi, koliko često, i je li materijal prikladan za vježbu.”

## Što slajd dokazuje

Motivira zašto treba fonetski kontroliran tekst, a ne samo gramatički hrvatski tekst.

## Dodatno pojašnjenje

Tri razine problema:

1. Korisnik ima slušni problem.
2. Terapeut želi ciljane foneme ili fonemske klase.
3. Materijal treba biti tekstualno i audio provjerljiv.

## Tehnička veza s projektom

Zato pipeline mora vratiti:

- foneme kandidata
- ukupni broj fonema
- broj fonema u ciljnoj klasi
- postotak zasićenja
- pass/fail status

---

# Slajd 3 — Istraživačka pitanja i doprinosi

## Što reći

“Glavno pitanje nije samo mogu li LLM-ovi generirati hrvatske riječi i rečenice. Rad ima četiri sloja: prvo, mogu li LLM-ovi predložiti fonemski ciljane hrvatske kandidate; drugo, može li Python deterministički provjeriti te kandidate; treće, mogu li validirani kandidati postati tehnički ispravan hrvatski audio preko TTS-a; i četvrto, koliko su ti audio zapisi razumljivi kroz ASR i slušnu provjeru?”

## Četiri doprinosa

1. Evaluacija LLM generiranja hrvatskih riječi/rečenica pod fonemskim ograničenjima.
2. Deterministički Python validator koji ne vjeruje LLM-u za brojanje fonema.
3. Usporedba ChatGPT Plus i lokalne Ollame.
4. TTS usporedba validiranih kandidata kroz eSpeak NG, Coqui VITS HR i SpeechT5 HR.
5. ASR WER/CER i slušna provjera kao dodatna procjena razumljivosti i prirodnosti audio materijala.

## Dodatno tehničko pojašnjenje

Model ne odlučuje je li nešto valjano. To je najvažnija dizajnerska odluka. Isto vrijedi i za audio: TTS ne dokazuje da je materijal klinički dobar, nego samo proizvodi audio koji zatim provjeravam tehnički, ASR-om i slušanjem.

LLM može pogriješiti jer:

- ne zna pouzdano brojati foneme
- može krivo tretirati `dž`, `lj`, `nj`
- može ponavljati iste kandidate
- može izmisliti pseudo-riječi
- može tvrditi da riječ postoji iako nije provjerena

## Ako pitaju

**Zašto ne koristiti LLM za validaciju?**  
Zato što validacija mora biti deterministička i ponovljiva. Ako dva puta pokrenem isti Python validator nad istim tekstom, dobit ću isti rezultat. Kod LLM-a to nije zagarantirano.

**Zašto su TTS i ASR dio istraživačkog pitanja?**  
Zato što cilj audiorehabilitacije nije samo tekstna lista, nego potencijalni audio materijal za vježbe. Zato nakon tekstne validacije provjeravam može li se materijal sintetizirati i koliko je audio razumljiv.

---

# Slajd 4 — Veza s radom Andrijašević i Vukelić

## Što reći

“Rad koji reproduciram koristi GPT-4 za generiranje hrvatskog govornog materijala za auditivni trening. Preuzimam pet fonemskih klasa, saturation level i format riječi/rečenica. Moja razlika je što uvodim determinističku Python validaciju i širi evaluacijski pipeline.”

## Što preuzimamo iz rada

- pet fonemskih klasa
- zasićenje ciljnom klasom
- riječi
- kratke rečenice
- usporedbu po klasama i razinama zasićenja

## Što mijenjamo

- ne vjerujemo modelu da broji foneme
- ne tretiramo prompt “provjeri HJP” kao dokaz
- spremamo CSV i Markdown izvještaje
- dodajemo PCD, TTS, ASR i slušnu provjeru

## Dodatna napomena

U paperu su tablice rezultat prikazivale po klasama i saturation levelima. Zato sam kasnije u prezentaciji dodao analogne tablice da usporedba bude metodološki ista.

---

# Slajd 5 — Fonemske klase i formula zasićenja

## Što reći

“Koristim pet fonemskih klasa: N, SN, S, SV i V. Svaki fonem pripada jednoj klasi. Za svaki kandidat brojim ukupne foneme i foneme ciljne klase.”

Formula:

`saturation = target_count / total_phonemes × 100`

## Primjer

Ako kandidat ima 10 fonema i 7 ih pripada ciljnoj klasi:

`7 / 10 × 100 = 70 %`

Ako je traženi prag 70 %, prolazi. Ako je 80 %, ne prolazi.

## Tehnički detalj

Parser mora posebno tretirati hrvatske višeslovne foneme:

- `dž`
- `lj`
- `nj`

Primjeri:

- `panj` → `p, a, nj`
- `polje` → `p, o, lj, e`
- `džep` → `dž, e, p`

Ako se to ne napravi, brojanje fonema je pogrešno.

## Ako pitaju

**Broje li se razmaci?**  
Ne. Razmaci služe za granice riječi, ali ne ulaze u ukupan broj fonema.

**Broji li se interpunkcija?**  
Ne. Interpunkcija se uklanja za fonemsko brojanje.

---

# Slajd 6 — Implementirani postupak

## Što reći

“Pipeline ide od generiranja kandidata do izvještaja. LLM generira, Python fonemizira i validira, a nakon toga se mogu raditi leksička i audio provjera.”

## Što se događa u pipelineu

1. Učitava se CSV ili se generiraju kandidati.
2. Tekst se normalizira.
3. Tekst se fonemizira.
4. Računa se zasićenje.
5. Provjeravaju se tehnički kriteriji.
6. Po potrebi se uključuje Hunspell.
7. Izvozi se HJP word-review.
8. Generiraju se izvještaji.
9. Validirani kandidati idu u TTS.

## Tehnički detalji

Svaki run ima:

- `run_id`
- config snapshot
- `all_candidates_<run_id>.csv`
- `validated_candidates_<run_id>.csv`
- `experiment_summary_<run_id>.csv`
- `report_<run_id>.md`

To znači da se svaki rezultat može povezati s konfiguracijom i ulaznim podacima.

---

# Slajd 7 — Tehnička implementacija: moduli i podaci

## Što reći

“Projekt je modularan. Svaki modul ima jednu odgovornost.”

## Moduli

### `phonemizer.py`

Radi:

- lowercase
- uklanjanje interpunkcije
- očuvanje hrvatskih znakova
- prepoznavanje `dž`, `lj`, `nj`
- vraćanje liste fonema

### `phoneme_classes.py`

Radi:

- definira pet fonemskih klasa
- omogućuje alias-e: `N`, `Niski`, itd.
- mapira fonem u klasu

### `validators.py`

Najvažniji modul za pass/fail.

Radi:

- `calculate_saturation`
- provjera znakova
- word/sentence word-count
- duplicate detection
- repeated-word detection
- dictionary/Hunspell status
- `failure_reasons`

### `metrics.py`

Radi:

- duplicate rate
- phoneme frequency
- phoneme class distribution
- PCD
- group summaries

### `generators.py`

Radi:

- manual CSV input
- Ollama generation
- prompt strategies
- parsing model outputa

### `pipeline.py`

CLI ulazna točka. Povezuje sve komponente.

### `tts.py` i `asr_eval.py`

Audio faza:

- TTS synthesis
- WAV normalization
- audio manifest
- ASR transcription
- WER/CER

## Ako pitaju

**Gdje je “glavna logika”?**  
Za tekst: `validators.py`. Za pokretanje eksperimenata: `pipeline.py`. Za foneme: `phonemizer.py`.

---

# Slajd 8 — Ključni algoritam: fonemizacija i validacija

## Što reći

“Najvažniji algoritam je deterministička fonemizacija i validacija kandidata.”

## Fonemizacija

Koraci:

1. `lowercase`
2. uklanjanje interpunkcije
3. normalizacija razmaka
4. očuvanje `č, ć, đ, š, ž`
5. longest-match-first za `dž`, `lj`, `nj`
6. ostala slova kao pojedinačni fonemi

## Validacija

Za svaki kandidat računa se:

- `phonemes`
- `total_phonemes`
- `target_count`
- `saturation_percentage`
- `passes_saturation`

Zatim se dodaju failure reasons.

## Failure reasons

- `failed_saturation`
- `invalid_characters`
- `wrong_word_count`
- `duplicate`
- `repeated_words`
- `dictionary_failed`

## Važan detalj

Kandidat može imati više grešaka istovremeno. Na primjer:

`mama mama mama`

Može imati:

- wrong word count ako je tip `word`
- repeated_words
- možda failed_saturation

Zato spremamo listu razloga, ne samo jedan razlog.

---

# Slajd 9 — Dizajn eksperimenata

## Što reći

“Eksperimenti su podijeljeni u tri razine.”

## Razina 1: reprodukcija rada

Riječi:

- 5 klasa
- 5 saturation levela: 40, 50, 60, 70, 80
- 11 riječi po uvjetu
- ukupno 275 riječi

Rečenice:

- 5 klasa
- 2 saturation levela: 50, 70
- kratke rečenice
- ukupno 210 rečenica

## Razina 2: Task 16 usporedba

Uspoređuje se:

- ChatGPT Plus
- lokalna Ollama `llama3.1:8b`
- `paper_style`
- `strict_plain_list`
- riječi i rečenice
- 50 % i 70 %

## Razina 3: audio

Samo kandidati koji su prošli tekstnu validaciju i HJP idu u TTS.

---

# Slajd 10 — Reprodukcija rada: riječi

## Što reći

“Ova tablica je napravljena po uzoru na Table II iz paper-a. U paperu ćelije prikazuju postotak riječi koje zadovoljavaju oba kriterija: saturation level i HJP/standardni hrvatski.”

## Kako je izračunato kod nas

Za svaku klasu i svaki saturation level:

`broj kandidata koji imaju passes_saturation=True i candidate_hjp_valid=yes / ukupan broj kandidata`

To je analog paper indikatoru “both criteria satisfied”.

## Važna napomena

Naš pipeline dodatno mjeri duplikate, ali ih ne ubacujemo u ovu tablicu jer želimo usporedbu s paper metodologijom. Duplikate prikazujemo u posebnim rezultatima.

## Zaključak

Naši rezultati su vrlo dobri za većinu klasa, ali postoji pad za teže slučajeve, posebno:

- SV na 70 %
- V na 80 %

To pokazuje da viši saturation level i određene klase otežavaju generiranje.

---

# Slajd 11 — Reprodukcija rada: rečenice

## Što reći

“Ovo je analog Table III iz paper-a. Za rečenice paper prikazuje postotak rečenica koje zadovoljavaju saturation level kriterij.”

## Kako je izračunato kod nas

Za svaku klasu i saturation level:

`broj rečenica s passes_saturation=True / ukupan broj rečenica`

## Zaključak

Na 50 % zasićenja rezultati su vrlo jaki. Na 70 % dolazi do pada, posebno za klasu V.

## Dodatno objašnjenje

Kod rečenica model ima više prostora nego kod riječi jer može kombinirati više riječi. Ali na visokom saturation levelu taj prostor se smanjuje, jer većina fonema mora pripadati ciljnoj klasi.

---

# Slajd 12 — ChatGPT Plus vs lokalni Ollama

## Što reći

“U punom Task 16 tekstnom eksperimentu ChatGPT Plus je znatno nadmašio lokalnu Ollamu.”

## Brojke

ChatGPT Plus:

- 797 kandidata
- 48,6 % tehnički valjano
- 85,9 % saturation pass
- 95,4 % Hunspell valid

Ollama:

- 757 kandidata
- 4,5 % tehnički valjano
- 4,6 % saturation pass
- 76,8 % Hunspell valid

## Interpretacija

ChatGPT Plus uglavnom razumije fonemski zadatak, ali se ponavlja. Ollama uglavnom ne pogađa fonemsko zasićenje.

## Važna obrana

Ne tvrdim da je Ollama kao platforma loša. Tvrdim da testirani lokalni model `llama3.1:8b` s ovim promptovima nije bio dovoljno pouzdan za strogi hrvatski fonemski zadatak.

---

# Slajd 13 — Što je najčešće pošlo krivo?

## Što reći

“Analiza grešaka pokazuje različite slabosti modela.”

## ChatGPT Plus

Glavni problem:

- duplikati

To znači:

Model često uspije pogoditi fonemski kriterij, ali generira iste ili vrlo slične riječi/rečenice u više uvjeta.

## Ollama

Glavni problem:

- failed_saturation

To znači:

Model generira tekst koji može izgledati hrvatski, ali ne zadovoljava traženi fonemski omjer.

## Zašto je ovo važno

Ako problem nisu fonemi nego duplikati, može se probati druga prompt strategija ili repair loop. Ako problem jest saturation, model ne kontrolira osnovni kriterij zadatka.

---

# Slajd 14 — Kako evaluator odlučuje valjanost + PCD

## Što reći

“Ovaj slajd objašnjava što znači tehnički valjano.”

## Tehnička valjanost

Kandidat mora proći:

1. `saturation_percentage >= saturation_level`
2. samo hrvatska slova i razmaci
3. ako je `word`, točno 1 riječ
4. ako je `sentence`, 3-5 riječi
5. nije duplikat u istom runu
6. nema ponovljene riječi u rečenici

Ako je uključen Hunspell dictionary mode, onda i:

7. `dictionary_word_validity == yes`

Ali u izvještajima razlikujem normalnu tehničku validaciju od technical + Hunspell valid rate.

## PCD

PCD = Phonetic Content Dissimilarity.

Naš paper-style PCD:

1. uzme dva kandidata
2. usporedi njihove fonemske sadržaje
3. dulji kandidat je nazivnik
4. računa koliko fonema duljeg kandidata nije podijeljeno s kraćim

Formula konceptualno:

`PCD = unmatched phonemes in longer candidate / length of longer candidate`

## Interpretacija PCD-a

- veći PCD = veća fonetska raznolikost
- manji PCD = kandidati su fonetski sličniji

Rezultat ukupno:

- ChatGPT Plus: 0,398
- Ollama: 0,274

U novoj verziji prezentacije dodatno prikazujem i PCD po klasama:

- ChatGPT Plus: N 0,474; SN 0,427; S 0,360; SV 0,423; V 0,487
- Ollama: N nema dovoljno validnih kandidata; SN 0,537; S 0,376; SV 0,522; V 0,667

Oprez u interpretaciji: kod Ollame su neke vrijednosti visoke, ali dolaze iz malog broja validnih grupa. Zato visok PCD kod Ollame ne znači da je Ollama bolja; prvo treba gledati da je imala vrlo malo validnih kandidata. PCD govori o raznolikosti među onim kandidatima koji su uopće ostali za usporedbu.

---

# Slajd 15 — Hunspell screening + ručni HJP

## Što reći

“Ovdje moram razlikovati tri stvari: tehnička validacija, Hunspell screening i HJP/manual review.”

## Hunspell

Hunspell je lokalni alat za provjeru riječi pomoću hrvatskog rječnika.

Pipeline koristi:

`hunspell -d hr_HR -l`

Logika:

- normaliziram kandidat u riječi
- svaku riječ šaljem Hunspellu
- ako Hunspell vrati riječ kao nepoznatu, kandidat dobiva `dictionary_failed`
- u CSV se spremaju invalid/unknown words

## HJP

HJP nije automatski scrap-an. To je namjerno, zbog sigurnosti i legalnosti.

Umjesto toga:

1. izvezem jedinstvene normalizirane riječi
2. ručno popunim `hjp_valid`
3. pipeline vrati tu odluku na kandidate

## Odnos Hunspell i HJP

Hunspell:

- brz
- automatski
- skalabilan
- nije savršen

HJP review:

- sporiji
- ručni
- bliži standardnojezičnom kriteriju iz paper-a

## Kako utječu na rezultate

Hunspell utječe na:

- Hunspell valid rate
- Technical + Hunspell valid rate
- lexical review queue

HJP utječe na:

- HJP/manual valid rate
- TTS-ready pool
- finalni izbor audio kandidata

## Caveat

Hunspell može odbiti valjanu hrvatsku fleksiju ili prihvatiti riječ koja nije dobra u terapijskom kontekstu. Zato nije finalna lingvistička ili klinička validacija.

---

# Slajd 16 — Što točno utječe na rezultate?

## Što reći

“Ovo je mapa svih metrika. U radu nema jedne valjanosti, nego više slojeva.”

## Slojevi

### 1. SL prolaznost

Mjeri samo fonemski kriterij.

Pada ako nema dovoljno fonema ciljne klase.

### 2. Tehnička valjanost

Mjeri Python pass/fail bez ljudske interpretacije.

Pada zbog:

- failed_saturation
- invalid_characters
- wrong_word_count
- duplicate
- repeated_words

### 3. Hunspell valid

Mjeri automatski leksički screening.

Pada ako Hunspell ne prepoznaje neku riječ.

### 4. Technical + Hunspell

Kandidat mora biti tehnički valjan i Hunspell-valid.

### 5. HJP/manual valid

Kandidat mora imati sve riječi ručno označene kao HJP-valid.

### 6. PCD

Mjeri raznolikost, ne valjanost.

### 7. TTS success

Mjeri je li audio tehnički generiran.

### 8. WER/CER i slušanje

Mjeri audio razumljivost/proxy kvalitetu, ali nije klinički dokaz.

## Ključna rečenica

“Zato uvijek moram reći o kojoj valjanosti govorim. Kandidat može proći saturation, ali pasti kao duplikat. Može proći Hunspell, ali biti semantički čudan. Može imati ispravan WAV, ali lošu prirodnost.”

---

# Slajd 17 — Audio faza

## Što reći

“Audio fazu radim tek nakon tekstne validacije. U suprotnom bih sintetizirao i evaluirao materijal koji već tekstualno nije dobar.”

## TTS modeli

- eSpeak NG
- Coqui VITS HR
- SpeechT5 HR

## Zašto isti tekst?

Da bi usporedba bila poštena. Ako svaki TTS dobije drugi tekst, ne znamo je li razlika zbog TTS-a ili teksta.

## WAV normalizacija

Svi audio izlazi se pretvaraju u:

- WAV
- mono
- 16 kHz
- 16-bit PCM

To je važno jer ASR i tehnička provjera trebaju usporediv format.

---

# Slajd 18 — TTS i ASR WER/CER

## Što reći

“Sva tri TTS sustava uspjela su sintetizirati svih 96 kandidata. To znači da je tehnički pipeline radio za sva tri adaptera.”

## Rezultati

- Coqui: WER 1,187; CER 0,693
- eSpeak: WER 1,076; CER 0,443
- SpeechT5: WER 0,967; CER 0,438

## ASR setup

Koristio se isti ASR profil:

- faster-whisper
- large-v3-turbo
- jezik: hrvatski
- lokalno

## WER/CER caveat

WER/CER nije savršena mjera izgovora.

Visok WER može značiti:

- TTS je loše izgovorio
- ASR nije dobro prepoznao
- materijal je fonetski neobičan

Zato WER/CER zovem proxy metrikom, ne kliničkim dokazom.

---

# Slajd 19 — Audio demo

## Što reći

“Sada puštam istu rečenicu kroz tri TTS sustava: `Draga rada radi.` Namjerno je ista rečenica da usporedba bude poštena.”

Redoslijed:

1. eSpeak NG
2. Coqui VITS HR
3. SpeechT5 HR

## Napomena

“Demo WAV datoteke su pojačane samo radi prezentacije. Originalni istraživački audio nije mijenjan.”

## Što očekivati

- eSpeak je često razumljiv, ali robotski
- SpeechT5 može zvučati prirodnije
- Coqui je u našem uzorku bio slabiji

---

# Slajd 20 — Slušna provjera

## Što reći

“Uz ASR sam napravio i ljudsku slušnu provjeru na uravnoteženom uzorku od 60 redaka: 20 po TTS sustavu.”

## Rezultati

eSpeak NG:

- razumljivost 4,65 / 5
- prirodnost 3,30 / 5

SpeechT5:

- razumljivost 3,35 / 5
- prirodnost 3,60 / 5

Coqui:

- razumljivost 2,15 / 5
- prirodnost 2,10 / 5

## Interpretacija

eSpeak je najrazumljiviji, SpeechT5 najprirodniji, Coqui najslabiji u ovom materijalu.

Važno:

ASR i čovjek nisu dali isti poredak. To je dokaz da ASR ne smije biti jedina audio evaluacija.

---

# Slajd 21 — Zaključak

## Što reći

“Zaključak je da je pipeline uspješno izgrađen. ChatGPT Plus je bolji generator od lokalne Ollame za ovaj strogi hrvatski fonemski zadatak, ali ni jedan model se ne smije koristiti bez determinističke validacije.”

## Glavni zaključci

1. LLM može pomoći u generiranju kandidata.
2. Python mora validirati foneme i kriterije.
3. ChatGPT Plus je puno bolji od testirane Ollame.
4. Viši saturation level otežava zadatak.
5. Hunspell je koristan screening, ali nije HJP.
6. HJP/manual review je potreban prije audio faze.
7. TTS je tehnički izvediv, ali klinička prikladnost traži ljudsku i stručnu procjenu.

## Završna rečenica

“Najvažniji rezultat nije samo lista riječi i rečenica, nego reproducibilan sustav koji sprječava da LLM sam sebi bude sudac.”

---

# Dodatna tehnička pitanja i spremni odgovori

## Kako točno radi duplicate detection?

Kandidat se normalizira. Ako je isti normalizirani tekst već viđen u istom runu, dobiva failure reason `duplicate`.

Primjer:

`Buba` i `buba.` nakon normalizacije postaju `buba`, pa se drugi kandidat smatra duplikatom.

## Zašto sentence mora imati 3-5 riječi?

To je kriterij zadatka i literature: kratke rečenice za auditivni trening, dovoljno kratke da budu kontrolirane i dovoljno duge da budu rečenice.

## Zašto invalid characters?

Da se izbace:

- brojke
- strani znakovi
- simboli
- čudni LLM artefakti

Hrvatski znakovi `č, ć, đ, š, ž` su dopušteni i čuvaju se.

## Zašto PCD nije validacija?

PCD ne kaže je li kandidat dobar, nego koliko je skup raznolik. Skup može imati visok PCD, ali lošu validnost. Ili može imati visoku validnost, ali nizak PCD ako se stalno ponavljaju slični obrasci.

## Kako HJP review utječe na rečenice?

Riječ po riječ.

Ako rečenica ima četiri riječi i sve su `hjp_valid=yes`, kandidat je HJP-valid.

Ako je barem jedna riječ `no`, cijela rečenica je HJP-invalid.

Ako je neka riječ `unsure` ili nedostaje, kandidat je `unsure`, osim ako već postoji riječ `no`.

## Zašto nije scraping HJP-a?

Zato što automatsko scrap-anjem HJP-a može biti pravno i tehnički problematično. Sigurniji i znanstveno transparentniji pristup je ručni word-review ili lokalni rječnik.

## Zašto su audio datoteke pojačane u demo mapi?

Samo radi prezentacije. SpeechT5 je bio tiši, pa su demo kopije normalizirane/pojačane da ih publika čuje. Istraživački originali ostaju nepromijenjeni.

## Što je najvažniji “computing” dio rada?

Najvažnije je da je validacija formalizirana u kodu:

- fonemizacija
- mapiranje fonema
- saturation formula
- failure reasons
- CSV reproducibilnost
- metrika PCD
- audio manifest i WER/CER

To pretvara LLM generiranje iz ručne aktivnosti u eksperimentalni pipeline.
