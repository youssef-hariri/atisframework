import os
import json
import re
import docx
import concurrent.futures
from openai import OpenAI
from tkinter import filedialog, Tk

# 1. API Setup
client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

# 2. Rubrics (Comprehensive Dictionary)
RUBRICS = {
    "stochastic_uncertainty": {
        "definition": "Inherent and irreducible unpredictability introduced by probabilistic machine learning models, whose outputs are non-deterministic and subject to statistical variance.",
        "indicators": [
            {"name": "non_deterministic_outputs", "description": "Results that are not fixed and can vary between runs."},
            {"name": "probabilistic_variance", "description": "Fluctuations in predictions and estimates based on statistical probability."},
            {"name": "model_drift", "description": "Performance decay over time due to changing data patterns."},
            {"name": "lack_of_reproducibility", "description": "The inability to consistently replicate AI-driven results."},
            {"name": "data_dependency", "description": "High sensitivity to historical data quality and relevance."},
            {"name": "non_linear_estimation", "description": "Complex relationships in cost and schedule that do not follow traditional linear paths."},
            {"name": "opaque_outcomes", "description": "Algorithmic decision-making complexities that lead to results that are hard to explain."},
            {"name": "dynamic_forecast_adjustment", "description": "The need to constantly update baselines as an indicator of underlying system instability."}
        ],
        "management_frictions": [
            {"name": "baseline_erosion", "description": "Probabilistic variance forcing project managers to repeatedly adjust forecasts and commitments."},
            {"name": "accountability_challenges", "description": "Opacity in outcomes making it difficult to assign clear responsibility for AI-derived decisions."}
        ]
    },
    "autocatalysis": {
        "definition": "The self-reinforcing, recursive acceleration of AI development that outstrips organizational and human capacity to adapt.",
        "indicators": [
            {"name": "recursive_innovation", "description": "AI tools being used to accelerate the development of further AI tools."},
            {"name": "skill_obsolescence_pace", "description": "Technical and managerial competencies becoming outdated faster than they can be replaced."},
            {"name": "judgment_substitution", "description": "The reconfiguration of human judgment as AI prediction capabilities improve."},
            {"name": "temporal_misalignment", "description": "The clash between 'AI time' (fast, iterative) and 'organizational time' (slow, sequential)."},
            {"name": "regulatory_lag", "description": "Governance and ethical frameworks emerging only after technical deployment."},
            {"name": "tool_proliferation", "description": "New frameworks released faster than they can be systematically evaluated or integrated."},
            {"name": "socio_technical_shift", "description": "Focus moving from economic benefits to human acceptance and ethics due to technical velocity."},
            {"name": "gen_AI_acceleration", "description": "Generative AI compounding the rate of change in innovation processes themselves."}
        ],
        "management_frictions": [
            {"name": "timeline_compression", "description": "Rapid tool obsolescence forcing architecture and testing re-evaluations mid-cycle."},
            {"name": "continuous_training_demand", "description": "The need for non-stop, modular training to keep up with emerging AI subtypes."},
            {"name": "integration_debt", "description": "Managing legacy AI components that are incompatible with new systems or standards."}
        ]
    },
    "process_disruption": {
        "definition": "Systemic friction emerging when non-linear, data-intensive AI workflows contradict traditional linear, phase-gated processes.",
        "indicators": [
            {"name": "socio_technical_transition", "description": "Moving from human-centric to hybrid human-AI collaboration models."},
            {"name": "workflow_brittleness", "description": "Increased vulnerability in linear processes when integrating adaptive AI."},
            {"name": "role_reconfiguration", "description": "Project managers shifting toward ethical judgment and system oversight."},
            {"name": "integration_friction", "description": "Challenges embedding AI into existing phase-based lifecycles."},
            {"name": "knowledge_clash", "description": "Tension between data-centric AI knowledge and tacit, experience-based human knowledge."},
            {"name": "procedural_nonlinearity", "description": "Iterative AI loops conflicting with sequential project methodologies."},
            {"name": "silo_breakdown", "description": "Cross-functional data needs undermining traditional departmental boundaries."},
            {"name": "ethical_automation_tension", "description": "Conflict between predictive automation and the need for human ethical oversight."}
        ],
        "management_frictions": [
            {"name": "legacy_inflexibility", "description": "Dynamic data needs hindered by legacy software built for static reporting."},
            {"name": "cultural_resistance", "description": "Distrust of data-centric approaches in favor of experiential knowledge and waterfall methods."},
            {"name": "role_transition_hurdles", "description": "Reskilling needs disrupting established hierarchies and decision-making authority."}
        ]
    },
    "high_customer_expectations": {
        "definition": "A perceptual gap where stakeholders-driven by hype-view AI as a flawless 'Magic Box'.",
        "indicators": [
            {"name": "dreams_vs_reality", "description": "Idealized visions of AI capability contrasted with practical, imperfect outputs."},
            {"name": "trust_understanding_gap", "description": "High optimism undermined by opaque or unsatisfactory behavior."},
            {"name": "paradoxical_expectations", "description": "Simultaneous high hopes and high perceived risk toward AI."},
            {"name": "magic_box_perception", "description": "Belief in AI as an infallible, autonomous solution."},
            {"name": "explainability_deficit", "description": "Frustration due to lack of transparent, interpretable decision-making."},
            {"name": "anthropomorphic_projection", "description": "Expecting human-like reasoning or reliability from algorithms."},
            {"name": "utility_mismatch", "description": "Assuming AI recommendations will perfectly align with personal or organizational goals."},
            {"name": "unfairness_barriers", "description": "Rejection of AI due to perceived biases or lack of fairness."}
        ],
        "management_frictions": [
            {"name": "feedback_dissonance", "description": "Users providing bug reports based on unrealistic benchmarks, requiring re-education labor."},
            {"name": "trust_erosion", "description": "Disillusionment in pilot phases leading to resistance to scaling and demands for redesign."}
        ]
    }
}

def read_docx(file_path):
    doc = docx.Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])

def clean_reasoner_output(raw_content):
    """Strips <think> tags and isolates the JSON array."""
    cleaned = re.sub(r'<think>.*?</think>', '', raw_content, flags=re.DOTALL)
    match = re.search(r'\[.*\]', cleaned, re.DOTALL)
    return match.group(0) if match else cleaned

def api_worker(transcript_data, spec_name, rubric, output_folder):
    """Processes one file for one specificity."""
    filename, text = transcript_data
    print(f"    [PASSING] {filename} for {spec_name}")
    
    prompt = f"""
    Role: You are an expert Qualitative Research Assistant specializing in In-Vivo coding and Latent Semantic Analysis for a DBA dissertation.
    Target Specificity: {spec_name}
    Theoretical Rubric: {json.dumps(rubric)}
    
    Transcript Data:
    {text}
    
    Strict Execution Rules:
    1. SPEAKER ISOLATION: Only analyze and extract quotes from "Person 2". Use "Person 1" only for situational context.
    2. SLANG DISCOVERY: Do not look for academic keywords. Instead, identify professional slang, everyday metaphors, and "human-floor" descriptions that match the 'descriptions' provided in the rubric.
    3. NEGATIVE CASES: Actively identify "Negative Cases" where Person 2 explicitly contradicts the theoretical construct or states that the specific friction is not present.
    4. ZERO-INFERENCE MAPPING: Every extracted quote must be mapped to a specific 'name' from the provided Indicators or Management Frictions in the rubric.
    5. OUTPUT FORMAT: You must output strictly as a valid JSON array of objects. Do not include any text before or after the JSON array.
    
    Required JSON Schema:
    [
      {{
        "expert_quote": "The exact verbatim quote from Person 2",
        "mapped_id": "The exact 'name' of the indicator or friction from the rubric",
        "is_negative_case": true/false,
        "rationale": "A brief academic explanation of the semantic link between the slang used and the theoretical definition."
      }}
    ]
    """
    
    try:
        response = client.chat.completions.create(
            model="deepseek-reasoner",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        cleaned_json = clean_reasoner_output(response.choices[0].message.content)
        
        output_name = f"{filename.replace('.docx', '')}_{spec_name}.json"
        with open(os.path.join(output_folder, output_name), "w") as f:
            f.write(cleaned_json)
        return True
    except Exception as e:
        print(f"    [ERROR] {filename} ({spec_name}): {e}")
        return False

def main():
    root = Tk(); root.withdraw()
    folder_path = filedialog.askdirectory(title="Select Transcripts Folder")
    if not folder_path: return

    output_folder = os.path.join(folder_path, "slang_results")
    os.makedirs(output_folder, exist_ok=True)

    # 1. Pre-load all transcripts into memory
    print("--- Pre-loading 48 Transcripts ---")
    transcripts = []
    for f in os.listdir(folder_path):
        if f.endswith(".docx"):
            transcripts.append((f, read_docx(os.path.join(folder_path, f))))

    # 2. Iterate specificities sequentially
    for spec_name, rubric in RUBRICS.items():
        print(f"\n--- STARTING BATCH: {spec_name} ---")
        
        # 3. Process all 48 files in parallel for THIS specificity
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(transcripts)) as executor:
            futures = [
                executor.submit(api_worker, t, spec_name, rubric, output_folder)
                for t in transcripts
            ]
            concurrent.futures.wait(futures)
            
    print("\n--- ALL BATCHES COMPLETE ---")

if __name__ == "__main__":
    main()
