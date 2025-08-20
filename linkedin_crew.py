# ==============================================================================
# LIBRERIE E CONFIGURAZIONE INIZIALE
# ==============================================================================
import os
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv
import textstat
import random

from crewai import Agent, Task, Crew, Process
from crewai_tools import ScrapeWebsiteTool
from langchain_openai import ChatOpenAI

# Carica le variabili d'ambiente dal file .env
load_dotenv()

# Imposta la lingua per textstat in italiano
textstat.set_lang("it_IT")

# ==============================================================================
# RISORSE E DOCUMENTAZIONE UTILE (come richiesto)
# =================================================z=============
# Documentazione CrewAI: https://docs.crewai.com/
# EU AI Act: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32024R1689
# OpenAI API: https://platform.openai.com/docs/
# LinkedIn API: https://learn.microsoft.com/en-us/linkedin/shared/integrations/social-actions
# ==============================================================================


# ==============================================================================
# FUNZIONI DI SUPPORTO E MODULARI
# ==============================================================================

def setup_llm():
    """
    Configura e restituisce il modello LLM (Large Language Model) da utilizzare.
    Utilizza gpt-4o come specificato, leggendo la chiave API dalle variabili d'ambiente.
    """
    try:
        llm = ChatOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name=os.getenv("OPENAI_MODEL_NAME", "gpt-4o"),
            temperature=0.7  # Un po' di creatività ma non troppa
        )
        return llm
    except Exception as e:
        print(f"Errore durante la configurazione dell'LLM: {e}")
        print("Assicurati di aver impostato correttamente OPENAI_API_KEY e OPENAI_MODEL_NAME nel tuo file .env")
        return None

def load_feedback(automatic_feedback_file="feedback.json", manual_feedback_file="feedback_manuale.json"):
    """
    Carica il feedback da file JSON, sia quello generato automaticamente
    sia quello inserito manualmente, per fornirlo all'Agente Generatore.
    """
    feedback_points = []
    # Carica feedback automatico se esiste
    if os.path.exists(automatic_feedback_file):
        with open(automatic_feedback_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "textual_feedback" in data:
                feedback_points.append(data["textual_feedback"])

    # Carica feedback manuale se esiste
    if os.path.exists(manual_feedback_file):
        with open(manual_feedback_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "manual_feedback" in data:
                feedback_points.extend(data["manual_feedback"])

    if not feedback_points:
        return "Nessun feedback precedente disponibile. Parti da zero."

    return "\n- ".join(["Basati su questo feedback per migliorare il post:"] + feedback_points)

def validate_post(post_content):
    """
    Valida un post generato secondo i requisiti di qualità.
    Controlla: lunghezza, presenza di hashtag e leggibilità.
    """
    print("\n--- INIZIO REPORT DI VALIDAZIONE ---")
    validation_report = {}

    # 1. Controllo Lunghezza
    word_count = len(post_content.split())
    is_length_valid = 200 <= word_count <= 300
    validation_report["word_count"] = {"count": word_count, "is_valid": is_length_valid}
    print(f"Conteggio parole: {word_count} (Valido: {is_length_valid})")

    # 2. Controllo Hashtag
    required_hashtags = ["#ResponsibleAI", "#EUAIAct"]
    found_hashtags = [tag for tag in required_hashtags if tag in post_content]
    are_hashtags_valid = len(found_hashtags) == len(required_hashtags)
    validation_report["hashtags"] = {"required": required_hashtags, "found": found_hashtags, "is_valid": are_hashtags_valid}
    print(f"Hashtag richiesti trovati: {found_hashtags} (Valido: {are_hashtags_valid})")

    # 3. Controllo Leggibilità (Flesch Reading Ease)
    # Nota: textstat funziona meglio con testi più lunghi, ma dà un'indicazione.
    # Un punteggio > 60 è considerato buono per un pubblico vasto.
    try:
        # Usiamo una versione inglese per la valutazione Flesch, dato che il modello è primariamente trainato in inglese
        # e le formule di leggibilità sono più standardizzate per questa lingua.
        textstat.set_lang("en_US")
        readability_score = textstat.flesch_reading_ease(post_content)
        is_readable = readability_score >= 60
        validation_report["readability"] = {"flesch_reading_ease_score": readability_score, "is_valid": is_readable}
        print(f"Punteggio di leggibilità (Flesch Reading Ease): {readability_score:.2f} (Valido: {is_readable})")
    except Exception as e:
        print(f"Impossibile calcolare la leggibilità: {e}")
        validation_report["readability"] = {"error": str(e)}

    # 4. Controllo Link
    has_links = "http://" in post_content or "https://" in post_content
    validation_report["links"] = {"found": has_links}
    print(f"Presenza di link esterni: {has_links}")

    print("--- FINE REPORT DI VALIDAZIONE ---\n")
    return validation_report

def get_linkedin_metrics_mock(post_content):
    """
    *** FUNZIONE MOCK (SIMULATA) ***
    Simula la raccolta di metriche dall'API di LinkedIn.
    In un'applicazione reale, qui andrebbe inserita la chiamata all'API di LinkedIn
    utilizzando un token OAuth 2.0.
    """
    print("--- ESECUZIONE VALUTAZIONE EFFICACIA (SIMULATA) ---")
    print("ATTENZIONE: Sto usando dati FITTIZI. Sostituire con chiamate reali all'API LinkedIn.")

    # Esempio di gestione dell'autenticazione (da implementare)
    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    if not access_token or access_token == "your_linkedin_access_token_here":
        print("Token di accesso LinkedIn non configurato. Impossibile procedere con una chiamata reale.")
        # In questo mock, procediamo comunque con dati fittizi

    # Dati fittizi per la simulazione
    mock_metrics = {
        "likes": random.randint(20, 150),
        "comments": random.randint(5, 40),
        "shares": random.randint(2, 25)
    }
    print(f"Metriche simulate raccolte: Likes={mock_metrics['likes']}, Commenti={mock_metrics['comments']}, Condivisioni={mock_metrics['shares']}")
    return mock_metrics

def analyze_and_generate_feedback(metrics, weights={"likes": 0.2, "comments": 0.5, "shares": 0.3}):
    """
    Calcola un punteggio di efficacia e genera un feedback testuale.
    """
    # Calcolo punteggio ponderato
    score = (metrics["likes"] * weights["likes"] +
             metrics["comments"] * weights["comments"] +
             metrics["shares"] * weights["shares"])

    # Generazione feedback testuale
    feedback_text = f"Il post ha ottenuto un punteggio di efficacia di {score:.2f}. "
    if metrics["comments"] < 10:
        feedback_text += "L'engagement (commenti) è basso. Prova a inserire una domanda più diretta o controversa per stimolare la discussione. "
    if metrics["shares"] < 5:
        feedback_text += "Le condivisioni sono poche. Forse il contenuto non è stato percepito come abbastanza unico o utile. Prova a includere un'infografica o un dato statistico sorprendente. "
    if metrics["likes"] > 100:
        feedback_text += "Ottimo numero di 'mi piace', il titolo e l'introduzione hanno funzionato bene. Continua su questa strada. "

    print(f"Punteggio di efficacia calcolato: {score:.2f}")
    print(f"Feedback generato per il prossimo ciclo: {feedback_text}")
    print("--- FINE VALUTAZIONE EFFICACIA ---\n")

    return {"effectiveness_score": score, "textual_feedback": feedback_text}

def save_results(post_content, validation, evaluation):
    """
    Salva il post generato, il report di validazione e il feedback
    in file JSON con timestamp e ID univoco.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    unique_id = str(uuid.uuid4())[:8]

    # Dati da salvare
    output_data = {
        "id": unique_id,
        "timestamp": timestamp,
        "generated_post": post_content,
        "validation_report": validation,
        "evaluation_feedback": evaluation
    }

    # Salva il post e il report
    post_filename = f"post_{timestamp}_{unique_id}.json"
    with open(post_filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    print(f"Post e report di validazione salvati in: {post_filename}")

    # Salva il feedback per il prossimo ciclo
    feedback_filename = "feedback.json"
    with open(feedback_filename, 'w', encoding='utf-8') as f:
        json.dump(evaluation, f, ensure_ascii=False, indent=4)
    print(f"Feedback per il prossimo ciclo salvato in: {feedback_filename}")


# ==============================================================================
# DEFINIZIONE AGENTI E TASK
# ==============================================================================

def create_linkedin_crew(llm, feedback_context):
    """
    Crea e assembla la crew di agenti con i loro task.
    """
    # Definizione dello strumento per il web scraping
    web_scraper = ScrapeWebsiteTool()

    # --- AGENTE 1: Generatore di Contenuti ---
    generator_agent = Agent(
        role="Esperto di Responsible AI e EU AI Act",
        goal="Creare un post LinkedIn settimanale di alta qualità, informativo e coinvolgente, incentrato sulla sicurezza, etica e governance dell'AI, in linea con l'EU AI Act.",
        backstory=(
            "Sei un rinomato stratega della comunicazione con una profonda conoscenza dell'ecosistema AI, "
            "specializzato nel tradurre concetti normativi e tecnici complessi in contenuti chiari e pragmatici per un pubblico enterprise. "
            "Il tuo stile è visionario ma concreto, simile a quello di Satya Nadella, ispirando fiducia e spingendo all'azione."
        ),
        llm=llm,
        tools=[web_scraper],
        verbose=True,
        allow_delegation=False
    )

    # --- AGENTE 2: Valutatore di Efficacia (in questo script, il suo lavoro è svolto da funzioni di supporto) ---
    # Nota: Non definiamo un secondo agente CrewAI per la valutazione perché
    # l'azione (chiamare API LinkedIn, calcolare metriche) non richiede un LLM.
    # Viene gestita da funzioni Python deterministiche dopo che il primo agente ha finito.
    # Questo approccio è più efficiente e meno costoso.

    # --- TASK: Generazione del Post ---
    generation_task = Task(
        description=f"""
        Crea un post per LinkedIn seguendo scrupolosamente queste direttive:

        1. **ARGOMENTO**: Scegli un tema specifico relativo alla Responsible AI, come prompt injection, trasparenza degli algoritmi, governance dei dati, o conformità all'EU AI Act.

        2. **FONTI**: Basa il tuo post su informazioni verificate provenienti da queste fonti autorevoli. Puoi usarne una o più.
           - EU AI Act ufficiale: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32024R1689
           - IEEE Ethics in AI: https://www.ieee.org/content/dam/ieee-org/ieee/web/org/about/initiatives/ieee-ethics-in-ai.pdf
           - MIT Technology Review (sezione AI): https://www.technologyreview.com/tag/artificial-intelligence/

        3. **STRUTTURA DEL POST**:
           - **Titolo Accattivante**: Massimo 10 parole. Deve essere incisivo (es. 'AI Sicura: Oltre la Conformità, Verso la Fiducia').
           - **Introduzione**: 3-4 frasi (40-60 parole). Inizia con una domanda provocatoria o un'affermazione audace per catturare l'attenzione.
           - **Corpo del Testo**: 10-12 righe (120-180 parole). Spiega il concetto chiave scelto. Includi un esempio pratico o un breve caso di studio per rendere il contenuto tangibile.
           - **Conclusione**: 2-3 righe (20-40 parole). Termina con una chiara call-to-action e 1-2 link pertinenti presi dalle fonti.

        4. **STILE E LINGUAGGIO**:
           - **Tono**: Visionario e pragmatico. Ispira i lettori ma fornisci anche consigli pratici.
           - **Linguaggio**: Chiaro, diretto e accessibile a un pubblico professionale non necessariamente tecnico. Evita il gergo complesso.

        5. **FORMATTAZIONE**:
           - **Lunghezza Totale**: Tra 200 e 300 parole.
           - **Hashtag Obbligatori**: Termina il post ESATTAMENTE con '#ResponsibleAI #EUAIAct'. Non aggiungere altri hashtag.

        6. **FEEDBACK DA CONSIDERARE**:
           {feedback_context}
        """,
        agent=generator_agent,
        expected_output="Un post per LinkedIn completo, formattato come testo semplice, pronto per essere copiato e incollato. Il post deve rispettare TUTTE le direttive fornite, inclusi lunghezza, struttura, tono e hashtag."
    )

    # Assembla la crew
    linkedin_crew = Crew(
        agents=[generator_agent],
        tasks=[generation_task],
        process=Process.sequential,
        verbose=2
    )

    return linkedin_crew

# ==============================================================================
# ESECUZIONE PRINCIPALE
# ==============================================================================

if __name__ == "__main__":
    print("--- AVVIO DEL PROCESSO DI CREAZIONE POST LINKEDIN ---")

    # 1. Configura LLM
    llm = setup_llm()

    if llm:
        # 2. Carica feedback esistente
        feedback_context = load_feedback()
        print("\n--- Feedback caricato per il generatore ---")
        print(feedback_context)
        print("-----------------------------------------\n")

        # 3. Crea e avvia la crew
        crew = create_linkedin_crew(llm, feedback_context)
        print("\n--- La CrewAI è pronta. Avvio del task di generazione... ---\n")
        generated_post = crew.kickoff()

        print("\n\n--- TASK DI GENERAZIONE COMPLETATO ---")
        print("Post generato dal sistema:")
        print("--------------------------------------------------")
        print(generated_post)
        print("--------------------------------------------------")

        # 4. Valida il post generato
        validation_report = validate_post(generated_post)

        # 5. Valuta l'efficacia (con dati simulati)
        mock_metrics = get_linkedin_metrics_mock(generated_post)
        evaluation_result = analyze_and_generate_feedback(mock_metrics)

        # 6. Salva tutti i risultati
        save_results(generated_post, validation_report, evaluation_result)

        print("\n--- PROCESSO COMPLETATO ---")
        print("Controlla i file JSON generati per i dettagli completi.")

    else:
        print("Processo interrotto a causa di un errore di configurazione dell'LLM.")

# ==============================================================================
# SUGGERIMENTI PER MIGLIORAMENTI FUTURI (come richiesto)
# ==============================================================================
# 1. Caching delle Fonti: Per evitare di scaricare le stesse fonti (es. EU AI Act)
#    ad ogni esecuzione, si potrebbe implementare un sistema di caching.
#    Prima di chiamare `ScrapeWebsiteTool`, controlla se il contenuto è già stato
#    scaricato di recente e salvato localmente.
#
# 2. Test A/B per Titoli: Modifica l'Agente Generatore per creare due o tre
#    varianti del titolo. Un altro task potrebbe poi scegliere il migliore
#    basandosi su metriche predittive di engagement (es. usando un modello addestrato).
#
# 3. Analisi di Sentiment sui Commenti: Nella versione reale con l'API di LinkedIn,
#    raccogli non solo il numero di commenti ma anche il loro testo. Usa una
#    libreria di NLP (es. NLTK, spaCy) per eseguire un'analisi di sentiment.
#    Questo darebbe un feedback qualitativo molto più ricco (es. "Il sentiment
#    era negativo, forse il tema era troppo controverso").
#
# 4. Parallelizzazione: Se i task fossero indipendenti (es. generare post per
#    piattaforme diverse), si potrebbe impostare `process=Process.parallel`
#    nella Crew per velocizzare l'esecuzione. In questo caso, il processo è
#    intrinsecamente sequenziale.
#
# 5. Integrazione Reale LinkedIn API: La funzione `get_linkedin_metrics_mock`
#    deve essere sostituita con una classe o un modulo che gestisca il flusso
#    OAuth 2.0 per l'autenticazione e le chiamate agli endpoint reali, con una
#    gestione robusta degli errori (rate limiting, token scaduti, etc.).
# ==============================================================================
