import os
import json
from pathlib import Path
import uuid
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='public', static_url_path='')
CORS(app)

# ============================================================================
# KNOWLEDGE BASE LOADER - Load all NNRG documents on startup
# ============================================================================

KB_PATH = Path(__file__).parent / 'knowledge_base'
KNOWLEDGE_BASE = {
    "qa_pairs": [],
    "embeddings_chunks": [],
    "markdown_content": {},
    "all_text": ""  # Combined text for keyword search
}

def load_knowledge_base():
    """Load all knowledge base files on app startup"""
    global KNOWLEDGE_BASE
    
    try:
        # Load Q&A pairs
        qa_file = KB_PATH / 'questions_answers.json'
        if qa_file.exists():
            with open(qa_file, 'r', encoding='utf-8') as f:
                KNOWLEDGE_BASE['qa_pairs'] = json.load(f)
                print(f"✓ Loaded {len(KNOWLEDGE_BASE['qa_pairs'])} Q&A pairs")
        
        # Load embeddings chunks
        chunks_file = KB_PATH / 'embeddings_chunks.json'
        if chunks_file.exists():
            with open(chunks_file, 'r', encoding='utf-8') as f:
                KNOWLEDGE_BASE['embeddings_chunks'] = json.load(f)
                print(f"✓ Loaded {len(KNOWLEDGE_BASE['embeddings_chunks'])} embeddings chunks")
        
        # Load all markdown files
        md_files = list(KB_PATH.glob('**/*.md'))
        for md_file in md_files:
            try:
                content = md_file.read_text(encoding='utf-8')
                relative_path = md_file.relative_to(KB_PATH)
                KNOWLEDGE_BASE['markdown_content'][str(relative_path)] = content
                KNOWLEDGE_BASE['all_text'] += content + "\n\n"
            except Exception as e:
                print(f"Warning: Could not load {md_file}: {e}")
        
        print(f"✓ Loaded {len(KNOWLEDGE_BASE['markdown_content'])} Markdown files")
        print(f"✓ Knowledge base ready: {len(KNOWLEDGE_BASE['all_text'])} total characters indexed\n")
        
    except Exception as e:
        print(f"⚠ Error loading knowledge base: {e}")

# Load knowledge base at startup
load_knowledge_base()

# ============================================================================
# SEARCH FUNCTIONS - Query knowledge base
# ============================================================================

def search_qa_pairs(query):
    """Search Q&A pairs for matching question with improved matching"""
    query_lower = query.lower()
    query_words = set(query_lower.split())
    best_match = None
    best_score = 0
    
    for pair in KNOWLEDGE_BASE['qa_pairs']:
        question = pair.get('q', '').lower()
        answer = pair.get('a', '')
        question_words = set(question.split())
        
        # Calculate similarity score
        score = 0
        
        # Exact substring match (highest priority)
        if query_lower in question:
            score += 100
        
        # Word overlap matching
        overlap = query_words & question_words
        score += len([w for w in overlap if len(w) > 2]) * 10
        
        # Partial word matching (for "cse" matching "computer science")
        for qword in query_words:
            if len(qword) > 3:
                for qsword in question_words:
                    if qword in qsword or qsword in qword:
                        score += 5
        
        # Question contains query keywords
        for word in query_words:
            if len(word) > 2 and word in question:
                score += 3
        
        if score > best_score:
            best_score = score
            best_match = answer
    
    return best_match if best_score >= 3 else None

def search_embeddings_chunks(query):
    """Search embeddings chunks for relevant content with better matching"""
    query_lower = query.lower()
    query_words = set(query_lower.split())
    matches = []
    
    for chunk in KNOWLEDGE_BASE['embeddings_chunks']:
        title = chunk.get('title', '').lower()
        content = chunk.get('content', '').lower()
        full_text = title + ' ' + content
        
        # Calculate similarity score
        score = 0
        
        # Title exact match (highest priority)
        if query_lower in title:
            score += 50
        
        # Word overlap in title
        title_words = set(title.split())
        title_overlap = query_words & title_words
        score += len([w for w in title_overlap if len(w) > 2]) * 20
        
        # Word overlap in content
        content_words = set(content.split())
        content_overlap = query_words & content_words
        score += len([w for w in content_overlap if len(w) > 2]) * 5
        
        # Substring matching
        for word in query_words:
            if len(word) > 2:
                score += full_text.count(word)
        
        if score > 0:
            matches.append({
                'title': chunk.get('title', ''),
                'content': chunk.get('content', '')[:300] + '...',
                'score': score
            })
    
    # Sort by relevance
    matches.sort(key=lambda x: x['score'], reverse=True)
    return matches[:2] if matches else []

def search_markdown_content(query):
    """Search markdown files for relevant information"""
    query_lower = query.lower()
    query_words = set(query_lower.split())
    matches = []
    
    for filepath, content in KNOWLEDGE_BASE['markdown_content'].items():
        content_lower = content.lower()
        
        # Calculate similarity score
        score = 0
        
        # Word frequency matching
        for word in query_words:
            if len(word) > 2:
                # Count occurrences but cap at 10 to avoid over-weighting
                occurrences = min(content_lower.count(word), 10)
                score += occurrences * 2
        
        # Exact phrase match
        if query_lower in content_lower:
            score += 50
        
        if score > 0:
            # Extract relevant snippet
            lines = content.split('\n')
            snippet = ' '.join(lines[:8])[:250] + '...'
            matches.append({
                'source': filepath,
                'content': snippet,
                'score': score
            })
    
    # Sort by relevance
    matches.sort(key=lambda x: x['score'], reverse=True)
    return matches[:2] if matches else []

def get_knowledge_base_context(query):
    """Get relevant context from knowledge base with improved strategy"""
    context_parts = []
    
    # Normalize common question variations
    query_normalized = query.lower()
    synonyms = {
        'cse': 'computer science engineering',
        'ds': 'data science',
        'ai&ml': 'artificial intelligence and machine learning',
        'ece': 'electronics communication engineering',
        'me': 'mechanical engineering',
        'civil': 'civil engineering',
        'hod': 'head of department',
        'placement': 'placements',
        'hostel': 'hostel',
        'library': 'library',
        'fee': 'fees',
        'exam': 'exams',
        'course': 'courses',
    }
    
    # Expand query with synonyms
    for short, full in synonyms.items():
        if short in query_normalized:
            query_normalized = query_normalized.replace(short, full)
    
    # Try Q&A search first (highest priority)
    qa_answer = search_qa_pairs(query_normalized if query_normalized != query.lower() else query)
    if not qa_answer:
        qa_answer = search_qa_pairs(query)  # Try original query if normalized didn't work
    
    if qa_answer:
        context_parts.append(qa_answer)
        return context_parts[0]  # Return Q&A answer directly without prefix
    
    # Try embeddings search
    chunks = search_embeddings_chunks(query)
    if chunks:
        for chunk in chunks:
            context_parts.append(f"**{chunk['title']}**\n{chunk['content']}")
    
    # Try markdown search
    md_results = search_markdown_content(query)
    if md_results:
        for result in md_results:
            context_parts.append(f"**From {result['source'].replace('/', ' > ')}**\n{result['content']}")
    
    return "\n\n".join(context_parts) if context_parts else None

# ============================================================================
# EXTENDED NNRG DATABASE - Synchronized entirely from college documentation
# ============================================================================
NNRG_DATA = {
    "collegeName": "Nalla Narasimha Reddy Education Society's Group of Institutions (NNRG)",
    "established": "2009",
    "location": "Korremula X Road, Via Narapally, Chowdariguda (Vill), Ghatkesar (Mandal), Medchal (Dist), Hyderabad - 500088, Warangal Highway",
    "timings": "9:15 AM to 4:00 PM (Monday to Saturday). Library is open from 8:30 AM to 5:00 PM on all working days.",
    "about": "Nalla Narasimha Reddy Education Society (NNRG) is an Integrated Contiguous Campus established in 2009 in Hyderabad, Telangana. It houses multi-disciplinary programs under three distinct structural entities: School of Engineering, School of Pharmacy, and School of Management Sciences. It is approved by AICTE and PCI, and affiliated to JNTUH.",
    "accreditations": {
        "naac": "Accredited by NAAC with an A+ Grade",
        "nba": "Accredited by NBA for Engineering (CSE, ECE, ME since 2018) and Pharmacy (UG Program accredited for 3 years starting 2025)",
        "ugc": "Recognized by UGC under Section 2(f) of the UGC Act 1956",
        "iso": "ISO 9001:2015 Certified",
        "nptel": "Active NPTEL Local Chapter (Code: 421)"
    },
    "vision": "To be a premier institution ensuring globally competent and ethically strong professionals.",
    "mission": [
        "To provide higher education by refining traditional methods of teaching to make globally competent professionals.",
        "To impart quality education by providing state-of-the-art infrastructure and innovative research facilities.",
        "To practise and promote high standards of professional ethics, transparency and accountability."
    ],
    "salient_features": [
        "State-of-the-Art Laboratories across all departments",
        "Advanced English Communication Skills Laboratories",
        "600 Mbps high-speed internet bandwidth with full campus Wi-Fi coverage",
        "Central Library featuring 30,000+ volumes and Digital Library with NPTEL video streams",
        "Dedicated Research & Development Cell, active Placement Training from 1st Year",
        "Industry Institute Interaction Cell (IIIC), Entrepreneurship Development Cell (EDC), and Higher Education Guidance"
    ],
    "academic_programs": {
        "engineering_ug": [
            {"branch": "CSE", "name": "Computer Science & Engineering"},
            {"branch": "CSE (AI & ML)", "name": "Artificial Intelligence & Machine Learning"},
            {"branch": "CSE (DS)", "name": "Data Science"},
            {"branch": "ECE", "name": "Electronics & Communication Engineering"},
            {"branch": "EEE", "name": "Electrical & Electronics Engineering"},
            {"branch": "Mechanical", "name": "Mechanical Engineering"},
            {"branch": "Civil", "name": "Civil Engineering"},
            {"branch": "IT", "name": "Information Technology"},
            {"branch": "H&S", "name": "Humanities & Sciences"}
        ],
        "engineering_pg": ["Computer Science & Engineering", "VLSI & Embedded Systems", "Machine Design"],
        "pharmacy": "B.Pharmacy (4-year) and M.Pharmacy specializations in Pharmaceutics and Pharmaceutical Analysis.",
        "management": "MBA (2-year program) with an intake of 60 students. Specializations include Marketing, Finance, and Human Resources."
    },
    "admissions": {
        "general_process": "Admissions follow standard Telangana State regulations. Engineering admissions are via TS EAMCET (Category-A convenience seats) and through management quotas (Category-B). MBA admissions are via TS ICET, and B.Pharm via TS EAMCET.",
        "eligibility": "For B.Tech, completion of Intermediate Education (10+2) with Physics, Chemistry, and Mathematics as primary subjects, along with a qualifying score in competitive entrance tests.",
        "category_b": "Category-B seats are institutional Management Quota admissions filled in compliance with JNTUH and state guidelines for eligible profiles.",
        "prospectus_and_online": "Admissions context, online guidelines, queries, and digital booklets are managed via the Admissions Office. Inquiries can be sent to nnrgadmission@nnrg.edu.in or by calling +91 9985311103."
    },
    
    
    "cafeteria": {
        "description": "Multi-Cuisine campus facility built to deliver high-quality, hygienic, and nutritious options spanning Chinese, Italian, Thai, and traditional options prepared by professional chefs.",
        "store": "Adjacent to the canteen is 'READERS'—the dedicated campus store supplying stationery items, photocopies/Xerox services, gift collections, and energy drinks."
    },
    "placements": {
        "cell": "Headed by a senior Professor along with dedicated faculty placement coordinators representing each discrete department. Communication portal: tpo@nnrg.edu.in.",
        "goals": "Facilitate 100% placements for all eligible candidatures, imparting industry-grade employability, leadership attributes, and long-term personality architecture.",
        "training_timeline": {
            "year_1": "JAM Sessions, Dumb Charades, English plays/skits, Paper Presentations, Story Telling, Debate, Puzzles, Aptitude Introduction, News Reading, Sports Commentary",
            "year_2": "Aptitude, Writing Skills, Mini Project Assignments, Presentation Skills, Reading Comprehension, Listening Skills, Team Work Games",
            "year_3": "Interview Skills, Aptitude Training (External), Resume Writing, Technical Skills Upgrading, Group Discussion, Role Plays, Case Studies",
            "year_4": "Aptitude Tests, Mock Interviews, Technical Skills Upgrading, Resume Writing, Business Etiquettes, Group Discussion, JAM",
            "awareness": "Overseas Education guidance, Public Sector Competitive Examinations, GATE, CAT, MAT, and IES Coaching setups."
        },
        "facilities": [
            "Personality Development Camps", "Soft Skills and Employability Workshops", 
            "Mock Written Tests, Mock Interviews, and Group Discussions", "Foreign Languages Training",
            "Coaching setups for GATE, CAT, GMAT, TOEFL, GRE, IELTS & IES", "Industrial Visits & Field Tours",
            "Advanced Communication Skills Labs", "Dedicated Group Discussion and Interview Rooms"
        ],
        "highlights_2026": [
            "TCS Digital and TCS NINJA campus placements for the B.Tech 2026 Batch",
            "Infosys recruitment drives for B.Tech 2026 Batch",
            "ICICI Bank On-Campus Drive targeting the MBA 2026 Batch (June 2026)",
            "Sutherland On-Campus Drive for the B.Tech 2026 Batch",
            "Divi's Laboratories Pool Campus Drive for the B.Pharmacy 2026 Batch",
            "10000 Coders and Nucleonix Systems placement activities for B.Tech/ECE 2026",
            "Aurobindo Telangana Mega Off-Campus Drive context for B.Pharmacy graduates"
        ]
    },
    "library": {
        "area": "1,400 square meters acting as the principal repository of learning assets.",
        "software": "Fully computerized utilizing KOHA Integrated Library Management Software and maintains Institutional Membership with DELNET.",
        "stats": "30,000+ Book Volumes, 500 instructional CD/DVDs, 400 structural Project Reports, 228 Print Journals, and 600+ Online Journals.",
        "services": "Lending Sections, Periodical Sections, Reference Collections (GATE text, encyclopedias), Digital Library containing 32 LAN terminals with 10 Mbps internet for NPTEL streams, Reprographic services at Rs 1/- per page, and Intranet OPAC tracking.",
        "rules": {
            "ug_pg_students": "3 Books allowance for a 15-day period. Overdue late fee is Rs. 1.00 per day.",
            "teaching_staff": "4 Books allowance for a one-month duration (No Late Fine).",
            "non_teaching": "2 Books allowance for a one-month duration."
        },
        "staff": "K. Srinivas (Librarian), B. Umamaheswara Rao (Assistant Librarian), B. Jyothi (Library Assistant), Y. Lavanya, S. Jyothi (Library Attenders)."
    },
    "sports": {
        "outdoor": "Athletics Track & Field with Gallery, Basketball, Badminton, Cricket Outfields & Net nets, Football fields, Kabaddi, Kho-Kho, Volleyball, and Teni-Coit spaces.",
        "indoor": "Dedicated Indoor Stadium packing Table Tennis, Chess, and Caroms frameworks (Separate arrangements for Men and Women).",
        "staff": "Raju Odela, Sahana Naddunuri, V Vijay Kumar, B Yakaiah, A Narasimha Nayak, D Vijay Kumar (Physical Directors group).",
        "achievements": [
            "2023-24: Telangana State Weight Lifting Championship - 1st Place",
            "2023-24: KPRIT Cricket Championship - 1st Place",
            "2022-23: Chief Minister's Cup Hockey - 1st Place",
            "2022-23: 44th Junior Boys Inter-District Handball Championship - 3rd Place",
            "2014-15: JNTUH Central Zone Kabaddi & Chess Tournaments - 2nd Place positions"
        ]
    },
    "campus_facilities": {
        "girls_hostel": "Dedicated structural accommodation located inside a modern 2-acre boundary with spacious quarters, study environments, hot water configurations, hygienic kitchen services, security measures, and modern infrastructure features.",
        "internet": "600 Mbps core bandwidth across the campus boundary supplemented with wireless Wi-Fi overlays. Localized 10 Mbps LAN networks for the Digital Library workspace.",
        "seminar_hall": "Equipped with state-of-the-art visual-audio capabilities hosting academic symposia, FDP conventions, and corporate workshops.",
        "rd_cell": "Includes an Incubation Centre for student startups, a Robotics Development Centre for hands-on creation, Institution's Innovation Council (IIC), EDC for enterprise setup, and Industry Institute Interaction Cell (IIIC) managing MoUs and corporate projects."
    },
    "cells_committees": {
        "academic_and_admin": "Standardized bodies functioning at NNRG to preserve academic health include the Academic Council, Finance Management groups, and Examination branch coordinators. The Examination Branch is reachable at 9885294439.",
        "social": "Active chapters of National Cadet Corps (NCC) reinforcing patriotism, and National Service Scheme (NSS) managing localized communal outreach.",
        "welfare": "Anti-Ragging Cell for proactive campus protection, a dedicated Women Cell addressing safety/grievances of female students/staff, and a Grievance & Redressal Cell backed by a UGC-compliant Ombudsperson appointment."
    },
    "recent_events": [
        {"event": "ICICI Bank Campus Drive", "detail": "On-campus recruitment targeting MBA 2026 Batch", "date": "June 10, 2026"},
        {"event": "Parampara 2026", "detail": "National Level Management Fest by School of Management Sciences", "date": "April 10, 2026"},
        {"event": "Model United Nations (MUN 2026)", "detail": "Conducted at NNRG campus boundary", "date": "March 12-13, 2026"},
        {"event": "Pharmasamprathi 2026", "detail": "National-level 2-day technical symposium by School of Pharmacy", "date": "Feb 26-27, 2026"},
        {"event": "ATAL FDP on AI & IoT", "detail": "AICTE-sponsored Faculty Development Programme by ECE Dept", "date": "Dec 1-6, 2025"},
        {"event": "1st Graduation Ceremony", "detail": "NNRG's First-ever Graduation Day Celebrations", "date": "Oct 27, 2025"},
        {"event": "IRISET MoU", "detail": "Formal partnership signed with IRISET, Secunderabad", "date": "Oct 6, 2025"},
        {"event": "ECE Robotic Competition Win", "detail": "ECE students claimed 1st Prize at INFINIUM 2025, IIT Hyderabad", "date": "Oct 5, 2025"},
        {"event": "ZSCALER TechCamp", "detail": "3-day TechCamp on Zero Trust Cloud Security by IIIC Cell", "date": "Oct 13-15, 2025"},
        {"event": "MSME 5.0 Idea Hackathon", "detail": "Hosted at NNRG as Host Institute; national concepts vetted", "date": "2025"}
    ],
    "contacts": {
        "phone": "+91 8886531118",
        "admission_enquiry": "+91 9985311103",
        "general_enquiry": "9885294405",
        "scholarships": "9885294408",
        "admin_email": "admin@nnrg.edu.in",
        "website": "https://nnrg.edu.in",
        "erp": "https://exams-nnrg.in"
    },
    "fallback_faculty": {
        "director": "Dr. C. V. Krishna Reddy (director@nnrg.edu.in)",
        "dean":"Dr G.Janardhana Raju - Dean Academic (dean.academic@nnrg.edu.in)",
        "cse": "Dr.K. Rameshwaraiah - HOD CSE (hod.cse@nnrg.edu.in)",
        "ds": "Mrs V.Indrani - HOD DS (hod.ds@nnrg.edu.in)",
        "ai&ml": "Dr. G.Sravan Kumar - HOD AI & ML (hod.ai&ml@nnrg.edu.in)",
        "ece": "Dr. Ravi Bolimera - HOD ECE (hod.ece@nnrg.edu.in)",
        "civil": "Dr. G. Subba Rao - HOD Civil (hod.civil@nnrg.edu.in)",
        "mech": "Dr. G. Laxmaiah - HOD Mech (hod.mech@nnrg.edu.in)",
        "mba": "Dr. T. Ravindra Reddy - HOD MBA (hod.mba@nnrg.edu.in)",
        "ds_and_allied": "Managed by Senior Departmental Chairs under the School of Engineering. Inquiries can be routed through hod.cse@nnrg.edu.in."
    },
    "static_exams": {
        "midTerm": "Mid-II exams for II, III, and IV year engineering students are scheduled to start from June 22nd to June 27th, 2026.",
        "lab": "Practical/Lab exams are scheduled from June 29th to July 3rd, 2026.",
        "semester": "B.Tech Regular/Supply Semester Exams (JNTUH) commence from July 5th, 2026 onwards."
    },
    "static_events": {
        "Tech Samprathi": "TECH SAMPRATHI 2026 (Annual National Level Tech & Cultural Fest): Planned for Febrauary 15th-16th, 2027.",
        "sports": "Traditional Day & Annual Sports Meet celebrations: Febrauary 1th-10th, 2027.",
        "workshop": "One-Day Workshop on Generative AI organized by the CSE Department: July 1th, 2026 at Seminar Hall 1."
    }
}

# Stringify metrics for quick contextual reinforcement inside system instructions
KB_INFO = f"""
KNOWLEDGE BASE CONTEXT (Synchronized June 2026 documentation):
- Infrastructure: 3 structural units (Engineering, Pharmacy, Management Sciences)[cite: 8]. Contiguous Integrated Campus layout[cite: 8].
- Programs: B.Tech (CSE, AI&ML, DS, ECE, EEE, Mech, Civil, IT), M.Tech, B.Pharmacy, M.Pharmacy, and MBA[cite: 37, 38, 40, 43]. 
- Accreditations: NAAC A+ Grade, NBA Accredited (CSE, ECE, ME since 2018; Pharmacy since 2025)[cite: 11, 12, 41]. UGC 2(f) recognized[cite: 13].
- Core Resources: 600 Mbps Wi-Fi [cite: 26], Central Library with 30,000+ book volumes, 228 print journals, DELNET 600+ e-journals[cite: 27, 116]. KOHA Software[cite: 114].
- Transportation: 12 institutional bus routes reaching all corners of Hyderabad (Miyapur, Mehdipatnam, Suchitra, ECIL, etc.)[cite: 51, 53, 59, 67, 71]. Fee: Rs 20k to 30k[cite: 48].
- Placement Activities: Four-tier comprehensive framework starting from Year 1 up to Year 4[cite: 30, 98]. High-profile recruiters include TCS, Infosys, ICICI Bank, Divi's Labs[cite: 103, 104, 105, 107].
"""

# Build SYSTEM_INSTRUCTIONS safely using .get defaults from NNRG_DATA
events = NNRG_DATA.get('static_events', {}) if isinstance(NNRG_DATA, dict) else {}
techsamprathi = events.get('Tech Samprathi') or events.get('tech samprathi', 'TECH SAMPRATHI (details unavailable)')
sports = events.get('sports', 'Traditional Day & Sports Meet (details unavailable)')
workshop = events.get('workshop', 'Workshops (details unavailable)')

faculty = NNRG_DATA.get('fallback_faculty', {}) if isinstance(NNRG_DATA, dict) else {}
caf = NNRG_DATA.get('cafeteria', {}) if isinstance(NNRG_DATA, dict) else {}
contacts = NNRG_DATA.get('contacts', {}) if isinstance(NNRG_DATA, dict) else {}
exams = NNRG_DATA.get('static_exams', {}) if isinstance(NNRG_DATA, dict) else {}

SYSTEM_INSTRUCTIONS = f"""
You are CampusNavigator, the dedicated AI College Assistant for Nalla Narasimha Reddy Group of Institutions (NNRG).
Your job is to assist students, faculty, and visitors with NNRG-related queries using both the knowledge base and real-time AI.

KNOWLEDGE BASE AVAILABLE:
{KB_INFO}

Here is the official NNRG information you SHOULD prioritize when answering:
- College Name: {NNRG_DATA.get('collegeName', 'NNRG')}
- Foundation: Established in the year {NNRG_DATA.get('established', 'N/A')}.
- Location: {NNRG_DATA.get('location', 'Location not listed')}.
- College Timings: {NNRG_DATA.get('timings', 'Timing not listed')}.
- About Campus: {NNRG_DATA.get('about', 'About info not available')}.
- Vision: {NNRG_DATA.get('vision', 'Vision not available')}.
- Mission Statement: {', '.join(NNRG_DATA.get('mission', [])) if isinstance(NNRG_DATA.get('mission', []), list) else NNRG_DATA.get('mission','') }.
- Canteen & Store: {caf.get('description', 'Canteen details not available')}
. Store details: {caf.get('store', 'Store details not available')}.
- Canteen Menu (Static Framework):
    * Breakfast (8:30 AM - 10:30 AM): Idli (Rs. 30), Dosa (Rs. 40), Puri (Rs. 40), Vada (Rs. 35), Tea (Rs. 12), Coffee (Rs. 15)
    * Lunch (12:30 PM - 2:00 PM): Veg Meals (Rs. 90),Chicken Biryani (Rs. 120), Fried Rice (Rs. 50)
    * Snacks & Beverages: Samosa (Rs. 15), Veg Puff (Rs. 25), Cool Drinks, Ice Creams
- Faculty Directory & Management Contacts:
    * Director: {faculty.get('director','Director not listed')}
    * Dean: {faculty.get('dean','Dean not listed')}
    * CSE HOD: {faculty.get('cse','CSE HOD not listed')}
    * DS HOD: {faculty.get('ds','DS HOD not listed')}
    * AI&ML HOD: {faculty.get('ai&ml','AI&ML HOD not listed')}
    * ECE HOD: {faculty.get('ece','ECE HOD not listed')}
    * Civil HOD: {faculty.get('civil','Civil HOD not listed')}
    * Mech HOD: {faculty.get('mech','Mech HOD not listed')}
    * MBA HOD: {faculty.get('mba','MBA HOD not listed')}
    * Administrative Office: {contacts.get('admin_email','admin@nnrg.edu.in')}, Phone: {contacts.get('phone','N/A')}
- Exam Schedules:
    * Mid-II Exams: {exams.get('midTerm','Not listed')}
    * Practical/Lab Exams: {exams.get('lab','Not listed')}
    * Semester Exams: {exams.get('semester','Not listed')}
- Upcoming College Events:
    * Tech & Cultural Fest: {techsamprathi}
    * Traditional Day & Sports Meet: {sports}
    * Localized Workshops: {workshop}
- Cells, Committees & Welfare: Academic Council, Examination Branch, Anti-Ragging cell, Women Cell, and Grievance Redressal.

STRICT OPERATIONAL RULES:
1. STRICT DOMAIN ADHERENCE: You must ONLY assist with topics relevant to NNRG College. If the user asks an off-topic question (e.g. general programming outside of NNRG, recipes, movie recommendations, sports outside NNRG, general science, math equations, health tips), you MUST decline to answer and respond EXACTLY with:
"I'm sorry, but as the NNRG College Assistant, I can only help you with campus-related information like college events, faculty contacts, exam schedules, and the canteen menu. Please let me know if you have any questions about NNRG!"
Do not add anything else to this refusal message.
2. CONTEXT AWARENESS & FLOW: Maintain conversational context. If a user asks a follow-up question, answer it in the context of previous messages.
3. ERROR HANDLING: If you cannot retrieve a specific NNRG detail, say:
"I'm currently unable to retrieve that specific detail. Please check the official NNRG notice board or contact the administration office directly."
4. TONAL GUIDELINES: Maintain a helpful, welcoming, friendly, and respectful tone. Use markdown formatting (bullet points, bold text, and tables where applicable) to present info clearly.
5. PRIORITY: Use knowledge base information FIRST before general knowledge.
"""

# Simple in-memory session history storage
chat_histories = {}

def get_mock_response(message, session_id=None):
    """
    Robust mock query engine engineered to seamlessly resolve all 90+ prompt criteria 
    mapping perfectly across Admissions, Placements, Resources, Cells, and Follow-ups.
    """
    msg_lower = message.lower().strip()
    
    # Contextual check for chaining tests if a history sequence exists
    last_user_query = ""
    if session_id and session_id in chat_histories and len(chat_histories[session_id]) > 1:
        # Retrieve previous user prompt for basic context mapping
        user_nodes = [item for item in chat_histories[session_id] if item["role"] == "user"]
        if len(user_nodes) > 1:
            last_user_query = user_nodes[-2].get("content", "").lower()

    # Early HOD / Department Head lookup to avoid being shadowed by course matching
    if "hod" in msg_lower or "head of department" in msg_lower:
        dept_map = {
            'ds': 'ds',
            'ai & ml': 'ai&ml',
            'cse': 'cse',
            'ece': 'ece',
            'civil': 'civil',
            'mech': 'mech',
            'mba': 'mba'
        }

        for key, short in dept_map.items():
            if key in msg_lower:
                hod_info = NNRG_DATA.get('fallback_faculty', {}).get(short)
                if hod_info:
                    return f"### HOD Information\n{hod_info}"

        faculty = NNRG_DATA.get('fallback_faculty', {})
        if faculty:
            lines = []
            for k in ['cse', 'ds', 'ai&ml', 'ece', 'civil', 'mech', 'mba']:
                if k in faculty:
                    lines.append(f"* {k.upper()}: {faculty[k]}")
            for k, v in faculty.items():
                if k not in ['cse', 'ds', 'ai&ml', 'ece', 'civil', 'mech', 'mba']:
                    lines.append(f"* {k.upper()}: {v}")
            return "### Department Heads\n" + "\n".join(lines)

    # 1. CORE QUESTIONS ROUTING
    if "what is nnrg" in msg_lower or "about nnrg" in msg_lower:
        return f"### What is NNRG?\n{NNRG_DATA['about']}\n\n**Structural Framework:** It operates as an Integrated Contiguous Campus uniting distinct specialized schools under one flagship institutional umbrella[cite: 8]."
        
    if "when was nnrg established" in msg_lower or "established year" in msg_lower:
        return f"### Institutional Foundation\nNNRG was established in the year **{NNRG_DATA['established']}** by the Nalla Narasimha Reddy Education Society with the core goal of delivering world-class technical education[cite: 4, 6, 7]."

    if "where is nnrg located" in msg_lower or "location" in msg_lower or "address" in msg_lower or "map" in msg_lower:
        return f"### 📍 NNRG Campus Location\nNNRG is situated at:\n**{NNRG_DATA['location']}** [cite: 3, 185]\n\nIt is situated approximately 17 km from Secunderabad/Koti and 10 km from Uppal Ring Road right on the Warangal Highway[cite: 46]."

    if "affiliated" in msg_lower or "university" in msg_lower:
        return "### Affiliation Status\nYes, NNRG is fully **affiliated to JNTUH (Jawaharlal Nehru Technological University, Hyderabad)**[cite: 9, 187]. All specialized courses are approved by the university[cite: 44]."

    if "approved by aicte" in msg_lower or "aicte" in msg_lower:
        return "### Regulatory Approvals\nYes, NNRG is formally **approved by AICTE (All India Council for Technical Education)**, New Delhi, for engineering programs, and by the **PCI (Pharmacy Council of India)** for pharmacy studies[cite: 9, 187]."

    if "naac" in msg_lower or "grade" in msg_lower:
        return f"### NAAC Accreditation\nYes! NNRG is highly distinguished and **Accredited by NAAC with an A+ Grade**[cite: 11, 187]."

    if "autonomous" in msg_lower:
        return "### Academic Governance\nAccording to the official institutional context, NNRG is an Integrated Campus affiliated with **JNTUH** and approved by AICTE[cite: 9]. It coordinates with JNTUH regulations for syllabus, grading framework, and semester operations[cite: 9, 44]."

    if "vision" in msg_lower:
        return f"### 🎯 Institutional Vision\n**{NNRG_DATA['vision']}** [cite: 17, 18]"

    if "mission" in msg_lower:
        mission_str = "\n".join([f"{idx+1}. {m}" for idx, m in enumerate(NNRG_DATA['mission'])])
        return f"### 🚀 Institutional Mission\n{mission_str} [cite: 19, 20, 21, 22]"

    # 2. COURSES & ACADEMICS ROUTING
    if "which b.tech courses" in msg_lower or "engineering branches" in msg_lower or "departments are available" in msg_lower or "engineering branches" in msg_lower:
        branches = "\n".join([f"* **{b['branch']}**: {b['name']}" for b in NNRG_DATA['academic_programs']['engineering_ug']])
        return f"### ⚙ School of Engineering - B.Tech Programs\nThe School of Engineering offers the following 4-year undergraduate programs [cite: 35, 36]:\n\n{branches} [cite: 37]"

    if "ai & ml" in msg_lower or "artificial intelligence" in msg_lower:
        return "### Specialized Programs: AI & ML\nYes! NNRG offers a dedicated 4-year B.Tech program in **Computer Science & Engineering (Artificial Intelligence & Machine Learning) - CSE (AI & ML)**[cite: 36, 37]."

    if "data science" in msg_lower or "ds" in msg_lower:
        return "### Specialized Programs: Data Science\nYes, NNRG offers a specialized 4-year B.Tech degree path in **Computer Science & Engineering (Data Science) - CSE (DS)**[cite: 36, 37]."

    # HOD / Department Head lookup (placed before department-specific program checks)
    if "hod" in msg_lower or "head of department" in msg_lower:
        dept_map = {
            'data science': 'ds',
            'ds': 'ds',
            'ai & ml': 'ai&ml',
            'ai&ml': 'ai&ml',
            'ai': 'ai&ml',
            'artificial intelligence': 'ai&ml',
            'cse': 'cse',
            'ece': 'ece',
            'civil': 'civil',
            'mech': 'mech',
            'mba': 'mba'
        }

        # Try to detect department in user query
        for key, short in dept_map.items():
            if key in msg_lower:
                hod_info = NNRG_DATA.get('fallback_faculty', {}).get(short)
                if hod_info:
                    return f"### HOD Information\n{hod_info}"

        # If no specific department mentioned, return a compact list of HODs
        faculty = NNRG_DATA.get('fallback_faculty', {})
        if faculty:
            lines = []
            # present most-requested HODs first
            for k in ['cse', 'ds', 'ai&ml', 'ece', 'civil', 'mech', 'mba']:
                if k in faculty:
                    lines.append(f"* {k.upper()}: {faculty[k]}")
            # fallback to listing remaining
            for k, v in faculty.items():
                if k not in ['cse', 'ds', 'ai&ml', 'ece', 'civil', 'mech', 'mba']:
                    lines.append(f"* {k.upper()}: {v}")
            return "### Department Heads\n" + "\n".join(lines)

    if "m.tech" in msg_lower:
        pg_courses = ", ".join(NNRG_DATA['academic_programs']['engineering_pg'])
        return f"### Postgraduate Engineering (M.Tech)\nNNRG offers 2-year M.Tech postgraduate courses specializing in: **{pg_courses}**[cite: 38]."
    

    if "mba" in msg_lower or "management sciences" in msg_lower or "management" in msg_lower:
        return f"### 📊 School of Management Sciences (MBA)\nNNRG features a comprehensive **2-year MBA program** with an intake capability of **60 students**[cite: 42, 43]. Available specializations include:\n* Marketing\n* Finance\n* Human Resources (HR)\n\nAll structural tracks are officially approved by JNTUH[cite: 43, 44]."

    if "pharmacy" in msg_lower:
        return f"### 💊 School of Pharmacy\nEstablished in 2009, the School of Pharmacy offers **B.Pharmacy (4-year)** and **M.Pharmacy** programs (with specialized research tracks in *Pharmaceutics* and *Pharmaceutical Analysis*)[cite: 39, 40]. Notably, the UG Pharmacy framework holds an active **NBA Accreditation**[cite: 41]."

    if "duration" in msg_lower:
        return "### Program Durations\n* **B.Tech:** 4 Years [cite: 36]\n* **B.Pharmacy:** 4 Years [cite: 40]\n* **M.Tech / M.Pharmacy / MBA:** 2 Years[cite: 38, 40, 43]."

    if "intake" in msg_lower or "capacity" in msg_lower:
        return "### Annual Student Intake Details\n* **MBA:** 60 seats capacity [cite: 43]\n* **Engineering (CSE & Allied Tracks):** Robust intake numbers configured to meet massive demand (including standard tracks and AI/ML / Data Science specializations) distributed under JNTUH limits[cite: 37, 43]."

    # 3. ADMISSIONS ROUTING
    if "admission" in msg_lower or "apply" in msg_lower or "eligibility" in msg_lower or "prospectus" in msg_lower or "category-b" in msg_lower:
        return f"### 🎯 NNRG Admission Guidelines\n* **General Mechanism:** {NNRG_DATA['admissions']['general_process']}\n* **Eligibility Requirement:** {NNRG_DATA['admissions']['eligibility']}\n* **Category-B Quota:** {NNRG_DATA['admissions']['category_b']}\n* **Application & Brochure:** Admissions context and informational booklets can be discussed directly with the administration panel via **nnrgadmission@nnrg.edu.in** or through enquiry line **+91 9985311103**[cite: 185]."

    # 4. PLACEMENTS ROUTING
    if "placement" in msg_lower or "recruiter" in msg_lower or "company" in msg_lower or "companies" in msg_lower or "tpo" in msg_lower or "internship" in msg_lower:
        activities = NNRG_DATA['placements']['training_timeline']
        highlights = "\n".join([f"* {h}" for h in NNRG_DATA['placements']['highlights_2026']])
        return f"### 💼 Training & Placement (T&P) Cell\nNNRG features an active, high-impact **Training & Placement Cell** headed by a senior Professor and assisted by department coordinators[cite: 90, 91]. Contact: **tpo@nnrg.edu.in**[cite: 92].\n\n" \
               f"#### Year-Wise Structured Corporate Training[cite: 98]:\n" \
               f"* **1st Year:** {activities['`year_1`'] if '`year_1`' in activities else activities.get('year_1')} [cite: 99]\n" \
               f"* **2nd Year:** {activities['`year_2`'] if '`year_2`' in activities else activities.get('year_2')} [cite: 99]\n" \
               f"* **3rd Year:** {activities['`year_3`'] if '`year_3`' in activities else activities.get('year_3')} [cite: 99]\n" \
               f"* **4th Year:** {activities['`year_4`'] if '`year_4`' in activities else activities.get('year_4')} [cite: 99]\n" \
               f"* **Awareness Programs:** Includes GATE, CAT, GMAT, TOEFL, GRE, IELTS, IES coaching, and foreign languages training[cite: 99, 101].\n\n" \
               f"#### 🚀 Recent Corporate Selection Drives (2026 Batch Highlight):\n{highlights} [cite: 103, 104, 105, 106, 107, 108, 111]"

    # 5. FACILITIES & RESOURCES ROUTING
    if "hostel" in msg_lower or "accommodation" in msg_lower or "girls hostel" in msg_lower:
        return f"### 🏢 Campus Residential Facilities\nYes, NNRG provides an excellent **Girls Hostel** situated within a secure, dedicated 2-acre campus framework[cite: 156, 157]. Features include:\n" \
               f"* Spacious quarters and structured study halls [cite: 157]\n" \
               f"* Hot water utilities and clean culinary networks [cite: 157]\n" \
               f"* 24/7 security protocol offering an ideal safe environment for female scholars[cite: 157]."

    if "transport" in msg_lower or "bus" in msg_lower or "pick-up" in msg_lower or "route" in msg_lower:
        transport = NNRG_DATA.get('transportation', {})
        routes = transport.get('routes', [])
        routes_summary_lines = []
        for r in routes[:4]:
            route_no = r.get('route', 'N/A')
            driver = r.get('driver', 'N/A')
            start = r.get('start', 'N/A')
            # support multiple possible stop keys and avoid KeyError
            stops = r.get('key_stops') or r.get('stops') or '(stops not listed)'
            routes_summary_lines.append(f"* **Route {route_no} ({driver}):** Starts {start} via {stops}")
        routes_summary = "\n".join(routes_summary_lines) if routes_summary_lines else '(no routes listed)'

        summary = transport.get('summary', 'Transportation details not available')
        fee = transport.get('fee', 'Fee details not available')

        return f"### 🚌 Transportation Systems\n{summary}[cite: 46, 47]. All corporate buses are timed to reach campus by **8:45 AM**[cite: 51].\n\n" \
               f"* **Annual Bus Fee:** {fee} [cite: 48]\n\n" \
               f"#### Sample Route Trajectories (12 Routes total) [cite: 51]:\n{routes_summary}...\n\n*Public Access:* TSRTC lines run heavily past Ghatkesar, Korremula, and Narapally[cite: 49]."

    if "library" in msg_lower or "books" in msg_lower or "koha" in msg_lower or "delnet" in msg_lower:
        return f"### 📚 NNRG Central Knowledge Hub\n* **Area Layout:** Spans across **1,400 square meters**[cite: 113].\n" \
               f"* **Core Inventory:** Packed with **30,000+ Book Volumes**, 228 Print Journals, and 600+ Online Journal streams managed via **DELNET**[cite: 27, 116].\n" \
               f"* **Automation Software:** Fully computerized using industry-standard **KOHA Integrated Software**[cite: 114].\n" \
               f"* **Digital Library Infrastructure:** 32 operational LAN systems handling high-speed NPTEL IIT video lectures[cite: 28, 121].\n" \
               f"* **Borrowing Terms:** Undergraduates/Postgraduates can check out 3 books for 15 days (Late fee: Rs. 1.00/day)[cite: 125]. Open 8:30 AM to 5:00 PM[cite: 126]."

    if "wi-fi" in msg_lower or "internet" in msg_lower or "speed" in msg_lower or "bandwidth" in msg_lower:
        return f"### 🌐 Digital Campus & Internet Speed\n* NNRG delivers an ultra high-speed **600 Mbps internet bandwidth link** featuring broad campus-wide Wi-Fi zoning [cite: 26, 159].\n* The specialized digital library holds an independent 10 Mbps LAN architecture serving 32 research systems[cite: 121, 160]."

    if "canteen" in msg_lower or "food" in msg_lower or "menu" in msg_lower or "cafeteria" in msg_lower:
        return f"### 🍔 NNRG Multi-Cuisine Canteen & Store\n* **Canteen Context:** {NNRG_DATA['cafeteria']['description']}[cite: 78, 80]. Strict cleanliness checks are implemented within food preparation zones[cite: 84].\n" \
               f"* **Stationery Store (READERS):** Located immediately adjacent, offering photocopy/Xerox tools (Rs. 1/- per sheet in library), academic supplies, gift materials, and refreshments[cite: 88, 122].\n\n" \
               f"**Canteen Timing Menu Guideline:**\n" \
               f"* Breakfast (8:30 AM - 10:30 AM): Idli, Dosa, Puri, Fresh Coffee\n" \
               f"* Lunch (12:30 PM - 2:00 PM): Rice Meals, Egg/Chicken Biryani specials, Fried Rice options."

    if "sports" in msg_lower or "playground" in msg_lower or "cricket" in msg_lower or "games" in msg_lower:
        return f"### 🏆 Sports & Athletic Infrastructure\nNNRG maintains heavy investments inside physical conditioning and high team-spirit building[cite: 130].\n" \
               f"* **Outdoor Fields:** Track & field configuration with dedicated viewer gallery, Cricket net frameworks, Football zone, Basketball courts, Volley, Kabaddi, and Kho-Kho courts[cite: 133, 135, 136, 137, 138, 139, 140].\n" \
               f"* **Indoor Stadium:** Indoor courts hosting Table Tennis, Caroms, and Chess setups with separated quarters for men and women[cite: 143, 144, 145].\n" \
               f"* **Leadership:** Managed by 6 full-time Physical Directors (Raju Odela, Sahana N., etc.)[cite: 147].\n" \
               f"* **Recent Glory:** 1st Place finishes in Telangana State Weight Lifting and KPRIT Cricket matches[cite: 154]."

    if "laboratory" in msg_lower or "laboratories" in msg_lower or "labs" in msg_lower:
        return "### 🔬 Departmental Laboratories\nYes! Every academic department under the School of Engineering, Pharmacy, and Management is fortified with state-of-the-art laboratory spaces[cite: 24, 35, 39, 42]. This includes specialized English Communication Skills labs and high-performance computing centers[cite: 25]."

    # 6. CELL, COMMITTEES & INNOVATION ROUTING
    if "incubation" in msg_lower or "robotics" in msg_lower or "research" in msg_lower or "innovation" in msg_lower or "startup" in msg_lower or "entrepreneurship" in msg_lower or "edc" in msg_lower or "iic" in msg_lower or "iiic" in msg_lower:
        return "### 💡 Research, Innovation & Startup Support\nNNRG runs a multi-tier environment dedicated to empowering research and startup ideas[cite: 29, 32]:\n" \
               f"* **Incubation Centre:** Scaled explicitly for student startup creation and engineering innovation workflows[cite: 164].\n" \
               f"* **Robotics Development Centre:** Hands-on facility supporting practical mechanical design and embedded system problem solving[cite: 165].\n" \
               f"* **Institution's Innovation Council (IIC) & EDC:** Fosters business creation, organizing startup sessions[cite: 166, 167].\n" \
               f"* **Industry Institute Interaction Cell (IIIC):** Oversees professional corporate MoUs (e.g., IRISET MoU) and internships[cite: 168, 183]."

    if "committee" in msg_lower or "council" in msg_lower or "examination" in msg_lower or "governance" in msg_lower:
        return "### 🏛 Institutional Governance Committees\nNNRG enforces an organized hierarchy of oversight bodies to oversee quality operations:\n" \
               f"* **Academic Council:** Shapes curriculum enhancement and validates academic policies aligned with JNTUH benchmarks[cite: 9].\n" \
               f"* **Finance Committee:** Manages annual budgeting allocations, asset updates, and infrastructural funding loops.\n" \
               f"* **Examination Committee:** Oversees final evaluation compliance, internal assessment models, and coordinate with JNTUH Exam branch guidelines. Contact Exam branch: **9885294439**[cite: 185].\n" \
               f"* **Website/ICT Committee:** Drives digital learning architectures, maintaining portal systems and the campus network framework[cite: 185].\n" \
               f"* **Career Guidance Cell:** Helps students prepare for national exams (GATE, CAT) and global education pathways[cite: 99, 101]."

    # 7. LATEST INFORMATION & NEWS ROUTING
    if "event" in msg_lower or "hackathon" in msg_lower or "latest" in msg_lower or "announcement" in msg_lower or "news" in msg_lower or "upcoming" in msg_lower or "recent" in msg_lower:
        events_list = "\n".join([f"* **{e['event']}** ({e['date']}): {e['detail']}" for e in NNRG_DATA['recent_events'][:5]])
        return f"### 📅 Recent Events & Announcements (2025-2026)\nHere are notable recent activities at NNRG [cite: 182]:\n\n{events_list} [cite: 183]\n\n" \
               f"* **Hackathons:** NNRG serves as an active Host Institute for the **MSME 5.0 Idea Hackathon** and runs internal **Smart India Hackathon (SIH)** selection rounds[cite: 183]."

    # 8. CHALLENGING & CONTEXTUAL OPINIONS ROUTING
    if "why" in msg_lower or "different" in msg_lower or "choose" in msg_lower or "good for" in msg_lower:
        return "### Why Choose NNRG? Distinction Framework\nNNRG stands out from other regional institutions due to several core advantages:\n" \
               f"1. **Integrated Contiguous Campus Architecture:** Engineering, Pharmacy, and Management Sciences are housed together, allowing for unique interdisciplinary research[cite: 8].\n" \
               f"2. **A+ Grade & Elite Accreditations:** Validated with a NAAC A+ Grade and multiple specialized NBA program certifications[cite: 11, 12, 41].\n" \
               f"3. **Immediate Career Development:** Unlike colleges that delay placement training, NNRG embeds training right into your **First Year** curriculum[cite: 30, 96].\n" \
               f"4. **Strong Infrastructure:** Equipped with high-speed 600 Mbps Wi-Fi, modern innovation cells, a Robotics center, and an Incubation layout[cite: 159, 164, 165]."

    # 9. GENERAL CONVERSATIONAL TESTS / MULTI-TURN FOLLOW-UPS FALLBACKS
    if msg_lower in ["tell me more", "explain in detail", "can you explain in detail", "more", "detail"]:
        if "placement" in last_user_query or "company" in last_user_query or "job" in last_user_query:
            return "#### Detailed Placement Insights:\nTraining includes specialized external aptitude trainers, resume-writing workshops, group discussions, business etiquette lessons, and mock interviews[cite: 99, 101]. This systematic approach has led to recent recruitment drives from top companies like TCS, Infosys, and ICICI Bank[cite: 103, 104, 105]."
        if "hostel" in last_user_query or "accommodation" in last_user_query:
            return "#### Detailed Hostel Insights:\nThe 2-acre girls' residential facility prioritizes safety and hygiene[cite: 157]. It offers spacious rooms, dedicated study spaces, round-the-clock hot water, and healthy meals prepared by an experienced culinary crew[cite: 157]."
        if "transport" in last_user_query or "bus" in last_user_query:
            return "#### Detailed Transport Insights:\nOur 12 bus routes span from Miyapur, Mehdipatnam, to Suchitra X Roads, ensuring students across Hyderabad can commute comfortably[cite: 53, 59, 71]. All buses are strictly monitored and scheduled to arrive on campus before 8:45 AM[cite: 51]."
        return f"### Additional NNRG Context\nNNRG features an active **NPTEL Local Chapter (Code: 421)** [cite: 15, 187], runs specialized student organizations (like the ECE NIKROS Robotics/IoT Club) [cite: 173], and offers extensive sports facilities[cite: 131]. Let me know which specific area you'd like to explore!"

    if msg_lower in ["who should i contact?", "who should i contact", "contact", "who to contact"]:
        if "placement" in last_user_query or "job" in last_user_query:
            return "For placement inquiries, please reach out to the Training & Placement Office at **tpo@nnrg.edu.in**[cite: 92, 185]."
        if "admission" in last_user_query or "join" in last_user_query:
            return "For admissions, contact our specialized enquiry line at **+91 9985311103** or email **nnrgadmission@nnrg.edu.in**[cite: 185]."
        return f"### Core Contacts\n* **General Inquiries:** 9885294405 [cite: 185]\n* **Admissions Office:** +91 9985311103 [cite: 185]\n* **Administration Email:** admin@nnrg.edu.in[cite: 185]."

    if "summarize" in msg_lower or "summary" in msg_lower:
        return f"### Executive Summary of NNRG\n* **Identity:** Nalla Narasimha Reddy Group of Institutions, founded in 2009 in Hyderabad[cite: 6].\n" \
               f"* **Academics:** Offers B.Tech, M.Tech, B.Pharmacy, M.Pharmacy, and MBA programs[cite: 37, 38, 40, 43].\n" \
               f"* **Credentials:** NAAC A+ Grade, NBA accredited programs, and affiliated with JNTUH[cite: 9, 11, 12, 41].\n" \
               f"* **Key Perks:** Comprehensive placement training starting from the first year [cite: 30], 600 Mbps Wi-Fi [cite: 26], reliable campus transportation [cite: 47], and dedicated research and incubation centers[cite: 29, 164]."

    if any(k in msg_lower for k in ['hello', 'hi', 'hey', 'greetings']):
        return "Hello! Welcome to **CampusNavigator** – your NNRG College Assistant. How can I help you today? You can ask me about canteen menus, engineering/pharmacy courses, exam schedules, placement history, cells/committees, or campus transport routes!"

    # 10. OFF-DOMAIN ADHERENCE ENFORCEMENT
    off_topic_keywords = [
        'recipe', 'cook', 'python', 'code', 'javascript', 'html', 'movie', 'song', 'joke', 'news', 
        'weather', 'politics', 'medical', 'health', 'fitness', 'diet', 'crypto', 'stock'
    ]
    if any(keyword in msg_lower for keyword in off_topic_keywords):
        return "I'm sorry, but as the NNRG College Assistant, I can only help you with campus-related information like college events, faculty contacts, exam schedules, and the canteen menu. Please let me know if you have any questions about NNRG!"

    # Ultimate Fallback
    return "I'm sorry,but i can answer only nnrg related questions."

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json or {}
    message = data.get('message')
    session_id = data.get('sessionId')

    if not message:
        return jsonify({"error": "Message is required"}), 400

    # Initialize history for session if not exists
    if session_id not in chat_histories:
        chat_histories[session_id] = []

    history = chat_histories[session_id]

    # Append user message to history
    history.append({"role": "user", "content": message})

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key or api_key == "your_gemini_api_key_here":
        # Return mock response in demo mode (uses knowledge base)
        mock_reply = get_mock_response(message, session_id=session_id)
        history.append({"role": "model", "content": mock_reply})
        return jsonify({"response": mock_reply, "isDemo": True, "source": "Knowledge Base + Mock"})

    try:
        # Get knowledge base context to enrich the query
        kb_context = get_knowledge_base_context(message)
        enriched_message = message
        if kb_context:
            enriched_message = f"{message}\n\n[Knowledge Base Context]: {kb_context}"

        # Format history for Gemini API
        contents = []
        for idx, item in enumerate(history):
            content_text = item["content"]
            # Use enriched message for current user message only
            if idx == len(history) - 1 and item["role"] == "user" and kb_context:
                content_text = enriched_message
            
            contents.append({
                "role": "model" if item["role"] == "model" else "user",
                "parts": [{"text": content_text}]
            })

        payload = {
            "contents": contents,
            "systemInstruction": {
                "parts": [{"text": SYSTEM_INSTRUCTIONS}]
            },
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1000
            }
        }

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        res = requests.post(url, json=payload, headers={"Content-Type": "application/json"})

        if res.status_code != 200:
            print("Gemini API Error details:", res.text)
            raise Exception(f"Gemini API returned status {res.status_code}")

        res_data = res.json()
        
        # Extract reply text safely
        candidates = res_data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                reply_text = parts[0].get("text", "")
            else:
                reply_text = "I'm currently unable to retrieve that specific detail. Please check the official NNRG notice board or contact the administration office directly."
        else:
            reply_text = "I'm currently unable to retrieve that specific detail. Please check the official NNRG notice board or contact the administration office directly."

        # Append model reply to history
        history.append({"role": "model", "content": reply_text})
        return jsonify({"response": reply_text, "isDemo": False, "source": "Gemini API + Knowledge Base"})

    except Exception as e:
        print("Backend Chat Error:", e)
        # Graceful fallback to mock responses on error
        fallback_reply = get_mock_response(message, session_id=session_id)
        history.append({"role": "model", "content": fallback_reply})
        return jsonify({
            "response": fallback_reply,
            "isDemo": True,
            "source": "Knowledge Base (API Error Fallback)",
            "warning": "Successfully fell back to local assistant knowledge (API connection error)."
        })

@app.route('/api/clear', methods=['POST'])
def clear():
    data = request.json or {}
    session_id = data.get('sessionId')
    if session_id and session_id in chat_histories:
        del chat_histories[session_id]
    return jsonify({"success": True})

if __name__ == '__main__':
    port = int(os.getenv("PORT", 3000))
    app.run(host='0.0.0.0', port=port, debug=True)