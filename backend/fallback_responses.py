"""Offline fallback responses for demo/presentation mode.
Used when the Groq API rate limit is reached."""


def generate_fallback_reply(user_message: str, language: str) -> str:
    """Generate a helpful keyword-based reply when the LLM is unavailable.
    Matches the requested format: concise, bullet points, 200-250 words, 2 follow-up questions."""
    msg = user_message.lower()
    is_urdu = "Urdu" in language or "Arabic" in language
    is_hindi = "Hindi" in language
    is_chinese = "Chinese" in language

    def follow_ups(*questions):
        return "\n\n**Follow-up questions:**\n" + "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))

    def note():
        # The fallback response should look like a normal advisor response.
        return ""

    # Chinese scholarships
    if any(k in msg for k in ["china", "chinese", "中国", "中文", "中國"]):
        if is_chinese:
            return (
                "中国政府奖学金（CSC）是面向国际学生最受欢迎的奖学金之一。它由中国教育部资助，"
                "适用于本科、硕士和博士各个层次。申请者需要是非中国籍公民，身体健康，并具备相应的学历背景。"
                "该奖学金通常覆盖全额学费、校内免费住宿以及每月生活补贴。申请渠道主要有两种："
                "一是通过中国高校直接向国家留学基金委推荐，二是通过中国驻外使领馆推荐。\n\n"
                "申请时通常需要准备以下材料：\n"
                "- **最高学历证明和成绩单**，需经过公证或学校盖章。\n"
                "- **学习计划或研究计划**，说明来华学习的目的和研究方向。\n"
                "- **推荐信**，通常需要两封来自教授或雇主的推荐信。\n"
                "- **语言能力证明**，如HSK、雅思或托福成绩。\n"
                "- **体检表和无犯罪记录证明**。\n\n"
                "热门院校包括清华大学、北京大学、浙江大学和上海交通大学等。"
                "建议提前6到12个月准备材料，并仔细查看目标学校的英文授课项目。"
                + follow_ups(
                    "你想申请本科、硕士还是博士？",
                    "你的专业方向是什么，是否已有目标院校？",
                )
                + note()
            )
        return (
            "The Chinese Government Scholarship (CSC) is one of the most popular funding options for international students who want to study in China. "
            "It is funded by the Chinese Ministry of Education and is available for bachelor's, master's, and PhD programs. "
            "Applicants must be non-Chinese citizens, in good health, and hold the required academic qualifications. "
            "The scholarship usually covers full tuition, free on-campus accommodation, and a monthly living allowance. "
            "There are two main application routes: applying through a Chinese university that recommends you to the China Scholarship Council, "
            "or applying through the Chinese embassy in your home country.\n\n"
            "Typical documents required include:\n"
            "- **Academic transcripts and diploma**, notarized or stamped by your school.\n"
            "- **Study plan or research proposal** explaining your goals in China.\n"
            "- **Recommendation letters**, usually two from professors or employers.\n"
            "- **Language proof** such as HSK, IELTS, or TOEFL scores.\n"
            "- **Medical form and no-criminal-record certificate**.\n\n"
            "Popular universities include Tsinghua, Peking University, Zhejiang, and Shanghai Jiao Tong. "
            "Start preparing 6 to 12 months early and check each university's English-taught programs."
            + follow_ups(
                "Are you planning to apply for bachelor's, master's, or PhD?",
                "What is your intended field of study, and do you have a target university?",
            )
            + note()
        )

    # US scholarships
    if any(k in msg for k in ["usa", "us", "america", "american", "united states"]):
        return (
            "Studying in the United States can be expensive, but there are several scholarships and funding programs for international students. "
            "The most prestigious option is the Fulbright Foreign Student Program, which provides full funding for graduate-level study and research. "
            "It is highly competitive and requires strong leadership experience, excellent essays, and academic achievements. "
            "Another option is the Hubert Humphrey Fellowship, which is designed for mid-career professionals who want to spend ten months in the U.S. "
            "Many U.S. universities also offer merit-based scholarships that are automatically considered when you apply for admission. "
            "These awards are often based on your GPA, test scores, and overall application strength.\n\n"
            "Key requirements usually include:\n"
            "- **Standardized tests** such as GRE or GMAT for graduate programs, and SAT or ACT for undergraduate programs.\n"
            "- **English proficiency** through TOEFL or IELTS.\n"
            "- **Transcripts and recommendation letters** from professors or employers.\n"
            "- **Strong personal essays** that explain your goals and why you chose the program.\n\n"
            "Applying early and researching each university's funding policies will improve your chances."
            + follow_ups(
                "Which U.S. universities are on your shortlist?",
                "Do you have your GRE and TOEFL/IELTS scores ready?",
            )
            + note()
        )

    # UK scholarships
    if any(k in msg for k in ["uk", "britain", "british", "england", "chevening"]):
        return (
            "The United Kingdom offers several excellent scholarship opportunities for international students. "
            "The Chevening Scholarship is one of the most competitive, covering full tuition, living expenses, and flights for a one-year master's degree. "
            "It requires at least two years of work experience, leadership potential, and a strong application essay. "
            "Another major option is the Commonwealth Scholarship, which supports students from Commonwealth countries who would not otherwise be able to study in the UK. "
            "The GREAT Scholarship provides around £10,000 toward tuition at selected UK universities. "
            "Additionally, many UK universities offer their own merit-based scholarships for high-achieving international applicants.\n\n"
            "Common requirements include:\n"
            "- **A strong academic record** and relevant work experience for Chevening.\n"
            "- **IELTS or equivalent English test** score meeting the university requirement.\n"
            "- **A compelling personal statement** explaining your goals and how the UK degree will help.\n"
            "- **Two academic or professional references**.\n\n"
            "Start preparing at least six months before deadlines."
            + follow_ups(
                "Do you meet the two-year work experience requirement for Chevening?",
                "Which UK course or university interests you most?",
            )
            + note()
        )

    # CV / resume
    if any(k in msg for k in ["cv", "resume", "curriculum vitae"]):
        return (
            "A strong CV or resume is essential for scholarship and university applications. "
            "Scholarship committees often review hundreds of applications, so your CV should be clear, well-organized, and no longer than two pages. "
            "Start with your contact information, including your full name, professional email, phone number, and LinkedIn profile if you have one. "
            "Next, list your education in reverse chronological order, including your degree, institution, graduation year, and GPA if it is strong. "
            "After that, highlight your skills, especially those relevant to your field, such as programming languages, software tools, or certifications.\n\n"
            "Your CV should also include:\n"
            "- **Projects and research** that show hands-on experience in your area of interest.\n"
            "- **Work experience and internships**, with bullet points describing your responsibilities and achievements.\n"
            "- **Extracurricular activities and volunteering** that demonstrate leadership and teamwork.\n"
            "- **Awards, scholarships, and competitions** you have won.\n\n"
            "Tailor your CV for each scholarship and use action verbs to describe your accomplishments."
            + follow_ups(
                "Would you like me to review your existing CV?",
                "Which scholarship or program is this CV for?",
            )
            + note()
        )

    # SOP / personal statement
    if any(k in msg for k in ["sop", "personal statement", "statement of purpose", "essay"]):
        return (
            "A personal statement or statement of purpose is one of the most important parts of your scholarship or university application. "
            "It gives the committee insight into who you are beyond your grades and test scores. "
            "Start by explaining why you chose your field of study and what motivates you to pursue it. "
            "Then, describe your academic and professional background, focusing on experiences that prepared you for this program. "
            "Be specific about your achievements, such as projects, research, internships, or awards.\n\n"
            "A strong statement should also include:\n"
            "- **Why this university or country**: Show that you have researched the program and faculty.\n"
            "- **Your short-term and long-term goals**: Explain how this degree fits into your career plan.\n"
            "- **How the scholarship will help**: Connect the funding to your ability to achieve your goals.\n"
            "- **Honest, clear writing**: Avoid generic statements and support your claims with examples.\n\n"
            "Most statements are 500 to 1,000 words unless the university specifies otherwise."
            + follow_ups(
                "Which university or scholarship is this statement for?",
                "Would you like me to suggest a detailed outline?",
            )
            + note()
        )

    # CS / AI / tech career
    if any(k in msg for k in ["cs", "computer science", "ai", "artificial intelligence", "data science", "software", "programming"]):
        return (
            "Computer science offers a wide range of career paths, and the right choice depends on your interests and strengths. "
            "If you enjoy building products, software engineering is a strong option. "
            "Software engineers design, develop, and maintain applications and systems, and they need solid skills in data structures, algorithms, and at least one programming language such as Python, Java, or JavaScript. "
            "If you are interested in data and machine learning, you can pursue a career as a data scientist or AI engineer, working with large datasets, building predictive models, and using tools like TensorFlow or PyTorch. "
            "Cloud and DevOps engineering is another growing field focused on deploying and managing scalable infrastructure.\n\n"
            "Other promising paths include:\n"
            "- **Cybersecurity specialist**, protecting organizations from digital threats.\n"
            "- **Mobile or web developer**, creating applications for users worldwide.\n"
            "- **Researcher or professor**, advancing CS knowledge through publications.\n"
            "- **Product manager or technical founder**, leading tech products and startups.\n\n"
            "Building a strong GitHub portfolio and contributing to open-source projects will help you stand out."
            + follow_ups(
                "Which CS specialization interests you most?",
                "Do you want scholarship options for CS master's programs?",
            )
            + note()
        )

    # GRE/IELTS/TOEFL
    if any(k in msg for k in ["ielts", "toefl", "gre", "sat", "act", "english test"]):
        return (
            "Standardized tests are an important part of studying abroad, especially for English-speaking countries. "
            "The IELTS and TOEFL exams measure your English proficiency, and most universities require a minimum IELTS score of 6.5 or a TOEFL score of 80. "
            "Some top universities may ask for higher scores, so always check the specific requirements of your target programs. "
            "For graduate programs in the United States, the GRE is often required. "
            "A competitive GRE score is usually 310 or above, with strong scores in the quantitative section for STEM fields. "
            "For undergraduate admissions in the U.S., you may need the SAT or ACT instead.\n\n"
            "Here are some preparation tips:\n"
            "- **Plan for 2 to 3 months** of consistent study.\n"
            "- **Use official practice materials** and take full-length mock tests regularly.\n"
            "- **Focus on weak areas**, whether vocabulary, writing, or quantitative reasoning.\n"
            "- **Book your test date early** to avoid missing application deadlines.\n\n"
            "Good preparation can significantly improve your admission chances."
            + follow_ups(
                "Which test do you need to take?",
                "When is your planned test date?",
            )
            + note()
        )

    # Greeting / general
    if any(k in msg for k in ["hello", "hi", "hey", "salam", "assalam", "kia hal", "kya hal", "kese ho", "kaise ho"]):
        return (
            "Hello! I am your Career & Scholarship Advisor, and I am here to help you plan your academic and professional future. "
            "Whether you are looking for scholarships, choosing a career path, preparing your CV, or writing a personal statement, I can guide you step by step. "
            "I can also help you prepare for standardized tests such as IELTS, TOEFL, and GRE, and suggest universities in countries like China, the United States, the United Kingdom, and others. "
            "To give you the best advice, I will ask a few questions about your background, goals, and preferences. "
            "The more details you share, the more personalized my recommendations will be.\n\n"
            "I can help you with:\n"
            "- Finding scholarships that match your profile and target country.\n"
            "- Writing effective CVs and personal statements.\n"
            "- Choosing a career path in tech, business, medicine, engineering, or other fields.\n"
            "- Preparing documents and tests for study abroad.\n\n"
            "Feel free to tell me about your education, interests, and goals."
            + follow_ups(
                "Which country are you interested in studying in?",
                "What is your current education level and field of study?",
            )
            + note()
        )

    # Default
    return (
        "Thank you for reaching out. I am your Career & Scholarship Advisor, and I can help you build a clear plan for your studies and career. "
        "To give you the most useful advice, it helps to know a bit about your background and goals. "
        "Please share your current education level, field of interest, and the country where you would like to study. "
        "If you are looking for scholarships, let me know whether you need full funding or partial support. "
        "I can also help with practical tasks such as writing your CV, preparing your personal statement, or getting ready for English tests.\n\n"
        "Here is what we can work on together:\n"
        "- Identifying scholarships and funding opportunities that fit your profile.\n"
        "- Choosing a career path based on your skills and interests.\n"
        "- Preparing strong application documents.\n"
        "- Planning for standardized tests and university interviews.\n\n"
        "Tell me more about yourself so I can guide you better."
        + follow_ups(
            "Which country do you want to study in?",
            "What is your field of interest and current education level?",
        )
        + note()
    )
