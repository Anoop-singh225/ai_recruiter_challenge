import json
import csv
import argparse
import os
import sys
from datetime import datetime

# Reconfigure stdout/stderr to UTF-8 to prevent encoding crashes on Windows
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Consulting company names (case-insensitive)
CONSULTING_COMPANIES = {
    "accenture", "capgemini", "cognizant", "genpact ai", "hcl", "infosys", 
    "mindtree", "mphasis", "tcs", "tata consultancy services", "tech mahindra", "wipro"
}

# Core skills categories
CORE_EMBEDDINGS = ["embeddings", "retrieval", "dense retrieval", "hybrid retrieval", "semantic search", "sentence-transformers", "sentence transformers", "bge", "e5"]
CORE_VECTOR_DB = ["pinecone", "weaviate", "qdrant", "milvus", "opensearch", "elasticsearch", "faiss", "vector database", "vector search", "hybrid search"]
CORE_EVAL = ["ndcg", "mrr", "map", "evaluation", "ranking", "eval", "learning to rank", "ltr", "learning-to-rank"]

# Nice to have categories
NICE_FINETUNING = ["fine-tuning", "finetuning", "lora", "qlora", "peft", "parameter-efficient"]
NICE_LTR = ["xgboost", "lightgbm", "learning to rank", "ltr", "learning-to-rank"]
NICE_DISTRIBUTED = ["distributed", "inference optimization", "tensorrt", "onnx", "deepstream", "triton"]

def get_skill_score_and_matches(skills):
    embeddings_score = 0
    vector_db_score = 0
    python_score = 0
    eval_score = 0
    
    nice_finetuning_score = 0
    nice_ltr_score = 0
    nice_dist_score = 0
    
    matched_skills = []
    
    prof_weights = {"expert": 1.0, "advanced": 0.8, "intermediate": 0.5, "beginner": 0.2}
    
    for s in skills:
        name = s.get("name", "").lower()
        prof = s.get("proficiency", "beginner").lower()
        weight = prof_weights.get(prof, 0.2)
        
        # Check core embeddings
        if any(keyword in name for keyword in CORE_EMBEDDINGS):
            score = 10.0 * weight
            if score > embeddings_score:
                embeddings_score = score
                matched_skills.append(s.get("name"))
                
        # Check core vector db
        elif any(keyword in name for keyword in CORE_VECTOR_DB):
            score = 10.0 * weight
            if score > vector_db_score:
                vector_db_score = score
                matched_skills.append(s.get("name"))
                
        # Check python
        elif name == "python":
            score = 10.0 * weight
            if score > python_score:
                python_score = score
                matched_skills.append(s.get("name"))
                
        # Check core eval
        elif any(keyword in name for keyword in CORE_EVAL):
            score = 10.0 * weight
            if score > eval_score:
                eval_score = score
                matched_skills.append(s.get("name"))
                
        # Check nice-to-have fine-tuning
        elif any(keyword in name for keyword in NICE_FINETUNING):
            score = 5.0 * weight
            if score > nice_finetuning_score:
                nice_finetuning_score = score
                matched_skills.append(s.get("name"))
                
        # Check nice-to-have ltr
        elif any(keyword in name for keyword in NICE_LTR):
            score = 5.0 * weight
            if score > nice_ltr_score:
                nice_ltr_score = score
                matched_skills.append(s.get("name"))
                
        # Check nice-to-have distributed/inference
        elif any(keyword in name for keyword in NICE_DISTRIBUTED):
            score = 5.0 * weight
            if score > nice_dist_score:
                nice_dist_score = score
                matched_skills.append(s.get("name"))
                
    core_score = embeddings_score + vector_db_score + python_score + eval_score
    nice_score = nice_finetuning_score + nice_ltr_score + nice_dist_score
    
    return core_score, nice_score, list(set(matched_skills))

def detect_honeypot(cand):
    # Check 1: expert/advanced proficiency skill with duration_months <= 0
    for s in cand.get("skills", []):
        prof = s.get("proficiency", "").lower()
        dur = s.get("duration_months", 0)
        if prof in ["expert", "advanced"] and dur <= 0:
            return True
            
    # Check 2: Profile YoE mismatch with sum of career history durations (> 3.0 years)
    profile_yoe = cand.get("profile", {}).get("years_of_experience", 0)
    total_months = sum(job.get("duration_months", 0) for job in cand.get("career_history", []))
    career_yoe = total_months / 12.0
    if abs(profile_yoe - career_yoe) > 3.0:
        return True
        
    # Check 3: Worked at Krutrim or Sarvam AI before 2023 or for > 3 years (36 months)
    for job in cand.get("career_history", []):
        comp = job.get("company", "")
        dur = job.get("duration_months", 0)
        start_str = job.get("start_date", "")
        if comp in ["Krutrim", "Sarvam AI"]:
            if dur > 36:
                return True
            if start_str:
                try:
                    start_yr = datetime.strptime(start_str, "%Y-%m-%d").year
                    if start_yr < 2023:
                        return True
                except Exception:
                    pass
                    
    return False

def score_candidate(cand):
    # If candidate is a honeypot, assign score of -9999.0 (immediate exclusion)
    if detect_honeypot(cand):
        return -9999.0, [], {}
        
    profile = cand.get("profile", {})
    history = cand.get("career_history", [])
    skills = cand.get("skills", [])
    signals = cand.get("redrob_signals", {})
    
    # 1. Experience Years Score (Max: 20 points)
    # Target: 5 to 9 years
    yoe = profile.get("years_of_experience", 0.0)
    exp_score = 0.0
    if 5.0 <= yoe <= 9.0:
        exp_score = 20.0
    elif 4.0 <= yoe < 5.0:
        exp_score = 15.0
    elif 9.0 < yoe <= 12.0:
        exp_score = 15.0
    elif 3.0 <= yoe < 4.0:
        exp_score = 8.0
    elif 12.0 < yoe <= 15.0:
        exp_score = 8.0
    else:
        exp_score = 0.0 # Outside reasonable experience range
        
    # 2. Skill Match Scores (Max: 40 core, 15 nice-to-have)
    core_skill_score, nice_skill_score, matched_skills = get_skill_score_and_matches(skills)
    
    # Nice-to-have: HR-tech/Marketplace summary search (Max: 5 points)
    hr_tech_score = 0.0
    summary_lower = profile.get("summary", "").lower()
    headline_lower = profile.get("headline", "").lower()
    for keyword in ["hr-tech", "recruiting tech", "talent intelligence", "marketplace", "job board", "recruitment", "recruiter"]:
        if keyword in summary_lower or keyword in headline_lower:
            hr_tech_score = 5.0
            break
            
    nice_score = nice_skill_score + hr_tech_score
    
    # Base Raw Score (Max: 80.0 points)
    base_score = core_skill_score + nice_score + exp_score
    
    # 3. Disqualifiers (Multipliers, default 1.0)
    dq_mult = 1.0
    
    # consulting-only check
    if history:
        all_consulting = True
        for job in history:
            comp = job.get("company", "").lower()
            if not any(c_firm in comp for c_firm in CONSULTING_COMPANIES):
                all_consulting = False
                break
        if all_consulting:
            dq_mult *= 0.1 # Severe penalty for consulting-only background
            
    # pure research check
    if history:
        all_research = True
        for job in history:
            title = job.get("title", "").lower()
            if not any(k in title for k in ["researcher", "research associate", "research assistant", "academic", "postdoc", "ph.d. candidate", "phd", "fellow"]):
                all_research = False
                break
        if all_research:
            dq_mult *= 0.2 # Severe penalty for pure research environment
            
    # non-coding architect/manager check
    if history:
        # Check current/most recent job
        recent_job = history[0]
        title = recent_job.get("title", "").lower()
        dur = recent_job.get("duration_months", 0)
        is_lead_arch = any(k in title for k in ["architect", "manager", "delivery manager", "director", "lead", "principal"])
        is_coder = any(k in title for k in ["engineer", "developer", "programmer", "data scientist", "ml engineer"])
        if is_lead_arch and not is_coder and dur >= 18:
            dq_mult *= 0.5 # Penalty for non-coding architect
            
    # CV/speech/robotics only check (no NLP/IR)
    has_cv_speech_robotics = False
    for s in skills:
        name = s.get("name", "").lower()
        if any(k in name for k in ["vision", "image", "cnn", "speech", "audio", "robotics", "ros", "yolo", "object detection", "ocr"]):
            has_cv_speech_robotics = True
            break
    has_nlp_ir = len(matched_skills) > 0 # we matched some core NLP/vector search skills
    if has_cv_speech_robotics and not has_nlp_ir:
        dq_mult *= 0.2 # Heavy penalty for CV-only without NLP/IR exposure
        
    # Title-chasers (switch jobs too frequently)
    if len(history) >= 3:
        avg_months = sum(job.get("duration_months", 0) for job in history) / len(history)
        if avg_months < 18:
            dq_mult *= 0.7 # Penalty for job hopping
            
    # Location Check
    loc = profile.get("location", "").lower()
    country = profile.get("country", "").lower()
    willing_reloc = signals.get("willing_to_relocate", False)
    
    loc_mult = 1.0
    if any(city in loc for city in ["noida", "pune", "delhi", "ncr"]):
        loc_mult = 1.15 # local boost
    elif country == "india" or "india" in loc:
        # Tier-1 cities
        if any(city in loc for city in ["hyderabad", "mumbai", "bangalore", "chennai", "kolkata"]):
            if willing_reloc:
                loc_mult = 1.0
            else:
                loc_mult = 0.5 # Penalty for refusing to relocate
        else:
            if willing_reloc:
                loc_mult = 0.8
            else:
                loc_mult = 0.4
    else:
        # Outside India
        if willing_reloc:
            loc_mult = 0.4
        else:
            loc_mult = 0.05 # Disqualified (cannot sponsor)
            
    dq_mult *= loc_mult
    
    # 4. Behavioral Signals Multipliers
    behavioral_mult = 1.0
    
    # Recruiter response rate
    resp_rate = signals.get("recruiter_response_rate", 0.0)
    behavioral_mult *= (0.5 + 0.5 * resp_rate)
    
    # Last active date check (reference local time: 2026-06-25)
    last_act_str = signals.get("last_active_date", "")
    if last_act_str:
        try:
            last_act_dt = datetime.strptime(last_act_str, "%Y-%m-%d")
            ref_dt = datetime(2026, 6, 25)
            inactive_days = (ref_dt - last_act_dt).days
            if inactive_days <= 30:
                behavioral_mult *= 1.15
            elif inactive_days <= 90:
                behavioral_mult *= 1.0
            elif inactive_days <= 180:
                behavioral_mult *= 0.75
            else:
                behavioral_mult *= 0.35 # Heavy penalty for inactive > 6 months
        except Exception:
            pass
            
    # Notice period
    notice_days = signals.get("notice_period_days", 0)
    if notice_days <= 30:
        behavioral_mult *= 1.15
    elif notice_days <= 60:
        behavioral_mult *= 1.0
    elif notice_days > 90:
        behavioral_mult *= 0.6 # Penalty for long notice period
        
    # Open to work flag
    if signals.get("open_to_work_flag", False):
        behavioral_mult *= 1.1
        
    # GitHub activity score
    gh_score = signals.get("github_activity_score", -1.0)
    if gh_score >= 70:
        behavioral_mult *= 1.1
    elif gh_score == -1:
        behavioral_mult *= 0.9 # Minor penalty for no GitHub
        
    # Interview completion rate
    int_rate = signals.get("interview_completion_rate", 0.0)
    behavioral_mult *= (0.7 + 0.3 * int_rate)
    
    # Saved by recruiters count
    saved_count = signals.get("saved_by_recruiters_30d", 0)
    behavioral_mult *= (1.0 + min(saved_count, 10) * 0.02)
    
    # Final combined score calculation
    final_score = (base_score / 80.0) * dq_mult * behavioral_mult
    final_score = max(0.0, min(1.0, final_score))
    
    details = {
        "yoe": yoe,
        "current_title": profile.get("current_title", ""),
        "current_company": profile.get("current_company", ""),
        "location": profile.get("location", ""),
        "country": profile.get("country", ""),
        "notice_period": notice_days,
        "resp_rate": resp_rate,
        "github": gh_score,
        "willing_reloc": willing_reloc,
        "last_active": last_act_str
    }
    
    return final_score, matched_skills, details

def generate_reasoning(cand_id, score, matched_skills, details):
    if score <= 0.0:
        return "Not a fit for this role."
        
    yoe = details.get("yoe", 0.0)
    title = details.get("current_title", "Engineer")
    company = details.get("current_company", "Product Company")
    location = details.get("location", "India")
    notice = details.get("notice_period", 0)
    resp = details.get("resp_rate", 0.0)
    github = details.get("github", 0)
    
    # Match skills list formatting
    skills_phrase = ""
    if matched_skills:
        selected_skills = sorted(matched_skills)[:3]
        skills_phrase = f"demonstrated production expertise in {', '.join(selected_skills)}"
    else:
        skills_phrase = "applied ML and systems software background"
        
    # Build dynamic components based on the candidate's actual stats to ensure high variety
    comp_intro = f"Senior AI Engineer profile with {yoe:.1f} years of experience, currently working as {title} at {company}."
    
    comp_fit = f"Strong match for the JD requirements; {skills_phrase}."
    
    # Signal component
    sig_parts = []
    if github >= 50:
        sig_parts.append(f"strong GitHub contributions (score: {github:.0f})")
    if notice <= 30:
        sig_parts.append(f"immediate availability ({notice} days notice)")
    if resp >= 0.7:
        sig_parts.append(f"high responsiveness on the platform ({resp:.0%})")
        
    comp_sig = ""
    if sig_parts:
        comp_sig = f"Highlights include: {', and '.join(sig_parts)}."
        
    # Concern component (honest concern)
    comp_concern = ""
    if notice > 60:
        comp_concern = f"Note: has a longer notice period of {notice} days, which we will need to buy out."
    elif not details.get("willing_reloc") and not any(city in location.lower() for city in ["noida", "pune", "delhi", "ncr"]):
        comp_concern = f"Note: located in {location}; requires local travel or remote setup."
    elif yoe < 5.0:
        comp_concern = f"Experience ({yoe:.1f} years) is slightly below the 5-9 years range, but skill depth justifies consideration."
    elif yoe > 9.0:
        comp_concern = f"Experience ({yoe:.1f} years) is above the target 5-9 range, but ideal for a founding lead role."
    else:
        comp_concern = f"Excellent candidate located in {location}."
        
    # Combine components dynamically
    sentences = [comp_intro, comp_fit]
    if comp_sig:
        sentences.append(comp_sig)
    sentences.append(comp_concern)
    
    reasoning = " ".join(sentences)
    # Ensure standard length limits
    if len(reasoning) > 280:
        reasoning = reasoning[:277] + "..."
    return reasoning

def main():
    parser = argparse.ArgumentParser(description="Rank candidates against a job description.")
    parser.add_argument('--candidates', required=True, help="Path to candidates.jsonl file.")
    parser.add_argument('--out', required=True, help="Path to output ranked CSV file.")
    args = parser.parse_args()
    
    if not os.path.exists(args.candidates):
        print(f"Error: candidates file not found at: {args.candidates}")
        sys.exit(1)
        
    print(f"Processing candidates from: {args.candidates}...")
    
    scored_candidates = []
    processed_count = 0
    honeypot_count = 0
    
    with open(args.candidates, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            processed_count += 1
            cand = json.loads(line)
            
            score, matched_skills, details = score_candidate(cand)
            
            if score == -9999.0:
                honeypot_count += 1
                continue
                
            scored_candidates.append({
                "candidate_id": cand["candidate_id"],
                "score": score,
                "matched_skills": matched_skills,
                "details": details
            })
            
    print(f"Total processed: {processed_count}")
    print(f"Honeypots skipped: {honeypot_count}")
    print(f"Valid candidates scored: {len(scored_candidates)}")
    
    # Sort candidates:
    # 1. By rounded score (4 decimal places) descending to match the CSV format
    # 2. By candidate_id ascending (to break ties deterministically as required by validator)
    scored_candidates.sort(key=lambda x: (-round(x["score"], 4), x["candidate_id"]))

    
    # Select top 100
    top_100 = scored_candidates[:100]
    
    # Write to CSV
    print(f"Writing top 100 candidates to {args.out}...")
    
    with open(args.out, "w", encoding="utf-8", newline="") as f_csv:
        writer = csv.writer(f_csv)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])
        
        for i, cand in enumerate(top_100):
            rank = i + 1
            cid = cand["candidate_id"]
            score = cand["score"]
            reasoning = generate_reasoning(cid, score, cand["matched_skills"], cand["details"])
            
            # Print top 10 details for console debug
            if rank <= 10:
                print(f"Rank {rank:2d} | {cid} | Score: {score:.4f} | YoE: {cand['details']['yoe']:.1f} | Loc: {cand['details']['location']} | Reason: {reasoning}")
                
            writer.writerow([cid, rank, f"{score:.4f}", reasoning])
            
    print(f"Ranking complete. Generated {args.out} successfully.")

if __name__ == "__main__":
    main()
