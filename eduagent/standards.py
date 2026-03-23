"""Standards database for Common Core (CCSS), NGSS, and C3 Framework."""

from __future__ import annotations

from typing import Optional

# Each entry: (code, description, grade_band)
STANDARDS: dict[str, list[tuple[str, str, str]]] = {
    "math": [
        # K-2
        ("CCSS.MATH.K.CC.1", "Count to 100 by ones and tens", "K"),
        ("CCSS.MATH.K.OA.1", "Represent addition and subtraction with objects, drawings, and equations", "K"),
        ("CCSS.MATH.1.OA.1", "Use addition and subtraction within 20 to solve word problems", "1"),
        ("CCSS.MATH.1.NBT.1", "Count to 120, starting at any number less than 120", "1"),
        ("CCSS.MATH.2.OA.1", "Use addition and subtraction within 100 to solve one- and two-step word problems", "2"),
        ("CCSS.MATH.2.NBT.1", "Understand that the three digits of a three-digit number represent hundreds, tens, and ones", "2"),
        # 3-5
        ("CCSS.MATH.3.OA.1", "Interpret products of whole numbers (e.g., 5 x 7 as the total in 5 groups of 7)", "3"),
        ("CCSS.MATH.3.NF.1", "Understand a fraction 1/b as the quantity formed by 1 part when a whole is partitioned into b equal parts", "3"),
        ("CCSS.MATH.4.OA.1", "Interpret a multiplication equation as a comparison (e.g., 35 = 5 x 7)", "4"),
        ("CCSS.MATH.4.NF.1", "Explain why a fraction a/b is equivalent to (n x a)/(n x b) using visual fraction models", "4"),
        ("CCSS.MATH.5.NF.1", "Add and subtract fractions with unlike denominators", "5"),
        ("CCSS.MATH.5.NBT.1", "Recognize that in a multi-digit number, a digit in one place represents 10 times as much as it represents in the place to its right", "5"),
        # 6-8
        ("CCSS.MATH.6.RP.1", "Understand the concept of a ratio and use ratio language to describe a ratio relationship", "6"),
        ("CCSS.MATH.6.EE.1", "Write and evaluate numerical expressions involving whole-number exponents", "6"),
        ("CCSS.MATH.7.RP.1", "Compute unit rates associated with ratios of fractions", "7"),
        ("CCSS.MATH.7.EE.1", "Apply properties of operations to add, subtract, factor, and expand linear expressions", "7"),
        ("CCSS.MATH.8.EE.1", "Know and apply the properties of integer exponents to generate equivalent numerical expressions", "8"),
        ("CCSS.MATH.8.F.1", "Understand that a function is a rule that assigns to each input exactly one output", "8"),
        ("CCSS.MATH.8.G.1", "Verify experimentally the properties of rotations, reflections, and translations", "8"),
        # 9-12
        ("CCSS.MATH.HSA.REI.1", "Explain each step in solving a simple equation as following from the equality of numbers", "9-12"),
        ("CCSS.MATH.HSA.CED.1", "Create equations and inequalities in one variable and use them to solve problems", "9-12"),
        ("CCSS.MATH.HSF.IF.1", "Understand that a function from one set to another assigns each element of the domain exactly one element of the range", "9-12"),
        ("CCSS.MATH.HSG.CO.1", "Know precise definitions of angle, circle, perpendicular line, parallel line, and line segment", "9-12"),
        ("CCSS.MATH.HSS.ID.1", "Represent data with plots on the real number line (dot plots, histograms, and box plots)", "9-12"),
    ],
    "ela": [
        # K-2
        ("CCSS.ELA-LITERACY.RL.K.1", "With prompting and support, ask and answer questions about key details in a text", "K"),
        ("CCSS.ELA-LITERACY.RF.K.1", "Demonstrate understanding of the organization and basic features of print", "K"),
        ("CCSS.ELA-LITERACY.RL.1.1", "Ask and answer questions about key details in a text", "1"),
        ("CCSS.ELA-LITERACY.W.1.1", "Write opinion pieces in which they introduce the topic, state an opinion, and supply a reason", "1"),
        ("CCSS.ELA-LITERACY.RL.2.1", "Ask and answer such questions as who, what, where, when, why, and how about key details", "2"),
        ("CCSS.ELA-LITERACY.W.2.1", "Write opinion pieces introducing the topic, stating an opinion, and supplying reasons", "2"),
        # 3-5
        ("CCSS.ELA-LITERACY.RL.3.1", "Ask and answer questions to demonstrate understanding of a text, referring explicitly to the text", "3"),
        ("CCSS.ELA-LITERACY.W.3.1", "Write opinion pieces on topics or texts, supporting a point of view with reasons", "3"),
        ("CCSS.ELA-LITERACY.RL.4.1", "Refer to details and examples in a text when explaining what the text says explicitly and when drawing inferences", "4"),
        ("CCSS.ELA-LITERACY.W.4.1", "Write opinion pieces on topics or texts, supporting a point of view with reasons and information", "4"),
        ("CCSS.ELA-LITERACY.RL.5.1", "Quote accurately from a text when explaining what the text says explicitly and when drawing inferences", "5"),
        ("CCSS.ELA-LITERACY.RI.5.1", "Quote accurately from a text and make relevant connections when explaining what the text says", "5"),
        # 6-8
        ("CCSS.ELA-LITERACY.RL.6.1", "Cite textual evidence to support analysis of what the text says explicitly as well as inferences drawn", "6"),
        ("CCSS.ELA-LITERACY.W.6.1", "Write arguments to support claims with clear reasons and relevant evidence", "6"),
        ("CCSS.ELA-LITERACY.RL.7.1", "Cite several pieces of textual evidence to support analysis of what the text says", "7"),
        ("CCSS.ELA-LITERACY.W.7.1", "Write arguments to support claims with clear reasons and relevant evidence", "7"),
        ("CCSS.ELA-LITERACY.RL.8.1", "Cite the textual evidence that most strongly supports an analysis of what the text says", "8"),
        ("CCSS.ELA-LITERACY.W.8.1", "Write arguments to support claims with clear reasons and relevant evidence", "8"),
        # 9-12
        ("CCSS.ELA-LITERACY.RL.9-10.1", "Cite strong and thorough textual evidence to support analysis of what the text says", "9-12"),
        ("CCSS.ELA-LITERACY.W.9-10.1", "Write arguments to support claims in an analysis of substantive topics or texts", "9-12"),
        ("CCSS.ELA-LITERACY.RL.11-12.1", "Cite strong and thorough textual evidence to support analysis, including determining where the text leaves matters uncertain", "11-12"),
        ("CCSS.ELA-LITERACY.W.11-12.1", "Write arguments to support claims in an analysis of substantive topics or texts, using valid reasoning and relevant evidence", "11-12"),
    ],
    "science": [
        # Middle School (6-8)
        ("MS-LS1-1", "Conduct an investigation to provide evidence that living things are made of cells", "6-8"),
        ("MS-LS1-2", "Develop and use a model to describe the function of a cell as a whole and ways cell parts contribute to the function", "6-8"),
        ("MS-LS1-6", "Construct a scientific explanation based on evidence for the role of photosynthesis in the cycling of matter and flow of energy", "6-8"),
        ("MS-LS1-7", "Develop a model to describe how food is rearranged through chemical reactions forming new molecules that support growth", "6-8"),
        ("MS-LS2-1", "Analyze and interpret data to provide evidence for the effects of resource availability on organisms and populations", "6-8"),
        ("MS-LS2-3", "Develop a model to describe the cycling of matter and flow of energy among living and nonliving parts of an ecosystem", "6-8"),
        ("MS-PS1-1", "Develop models to describe the atomic composition of simple molecules and extended structures", "6-8"),
        ("MS-PS1-2", "Analyze and interpret data on the properties of substances before and after the substances interact to determine if a chemical reaction has occurred", "6-8"),
        ("MS-PS2-1", "Apply Newton's Third Law to design a solution to a problem involving the motion of two colliding objects", "6-8"),
        ("MS-ESS1-1", "Develop and use a model of the Earth-sun-moon system to describe the cyclic patterns of lunar phases, eclipses, and seasons", "6-8"),
        ("MS-ESS2-1", "Develop a model to describe the cycling of Earth's materials and the flow of energy that drives this process", "6-8"),
        ("MS-ESS3-3", "Apply scientific principles to design a method for monitoring and minimizing a human impact on the environment", "6-8"),
        # High School (9-12)
        ("HS-LS1-1", "Construct an explanation based on evidence for how the structure of DNA determines the structure of proteins", "9-12"),
        ("HS-LS1-2", "Develop and use a model to illustrate the hierarchical organization of interacting systems that provide specific functions within multicellular organisms", "9-12"),
        ("HS-LS1-5", "Use a model to illustrate how photosynthesis transforms light energy into stored chemical energy", "9-12"),
        ("HS-LS1-7", "Use a model to illustrate that cellular respiration is a chemical process whereby the bonds of food molecules and oxygen molecules are broken and the bonds in new compounds are formed", "9-12"),
        ("HS-LS2-1", "Use mathematical and/or computational representations to support explanations of factors that affect carrying capacity of ecosystems", "9-12"),
        ("HS-PS1-1", "Use the periodic table as a model to predict the relative properties of elements based on the patterns of electrons in the outermost energy level", "9-12"),
        ("HS-PS1-2", "Construct and revise an explanation for the outcome of a simple chemical reaction based on outermost electron states and the periodic table", "9-12"),
        ("HS-PS2-1", "Analyze data to support the claim that Newton's second law of motion describes the mathematical relationship among the net force on a macroscopic object, its mass, and its acceleration", "9-12"),
        ("HS-ESS1-1", "Develop a model based on evidence to illustrate the life span of the sun and the role of nuclear fusion in the sun's core", "9-12"),
        ("HS-ESS2-1", "Develop a model to illustrate how Earth's internal and surface processes operate at different spatial and temporal scales to form continental and ocean-floor features", "9-12"),
    ],
    "history": [
        # Middle School (6-8)
        ("D1.1.6-8", "Explain how a question represents key ideas in the field of civics, economics, geography, or history", "6-8"),
        ("D1.2.6-8", "Explain points of agreement and disagreement experts have about interpretations of sources", "6-8"),
        ("D2.Civ.1.6-8", "Distinguish the powers and responsibilities of citizens, political parties, interest groups, and the media in a variety of governmental and nongovernmental contexts", "6-8"),
        ("D2.Civ.6.6-8", "Describe the roles of political, civil, and economic organizations in shaping people's lives", "6-8"),
        ("D2.Eco.1.6-8", "Explain how economic decisions affect the well-being of individuals, businesses, and society", "6-8"),
        ("D2.Geo.1.6-8", "Construct maps to represent and explain the spatial patterns of cultural and environmental characteristics", "6-8"),
        ("D2.His.1.6-8", "Analyze connections among events and developments in broader historical contexts", "6-8"),
        ("D2.His.3.6-8", "Use questions generated about individuals and groups to analyze why they and the developments they shaped are seen as historically significant", "6-8"),
        # High School (9-12)
        ("D1.1.9-12", "Explain how a question reflects an enduring issue in the field", "9-12"),
        ("D1.2.9-12", "Explain points of agreement and disagreement experts have about interpretations and applications of disciplinary concepts", "9-12"),
        ("D2.Civ.1.9-12", "Distinguish the powers and responsibilities of local, state, tribal, national, and international civic and political institutions", "9-12"),
        ("D2.Civ.6.9-12", "Critique relationships among governments, civil societies, and economic markets", "9-12"),
        ("D2.Eco.1.9-12", "Analyze how incentives influence choices that may result in policies with a range of costs and benefits for different groups", "9-12"),
        ("D2.Geo.1.9-12", "Use geospatial and related technologies to create maps to display and explain the spatial patterns of cultural and environmental characteristics", "9-12"),
        ("D2.His.1.9-12", "Evaluate how historical events and developments were shaped by unique circumstances of time and place as well as broader historical contexts", "9-12"),
        ("D2.His.3.9-12", "Use questions generated about individuals and groups to assess how the significance of their actions changes over time", "9-12"),
        ("D3.1.9-12", "Gather relevant information from multiple sources representing a wide range of views while checking the credibility of each source", "9-12"),
        ("D4.1.9-12", "Construct arguments using precise and knowledgeable claims, with evidence from multiple sources, while acknowledging counterclaims and evidentiary weaknesses", "9-12"),
    ],
}

# Subject name aliases
SUBJECT_ALIASES: dict[str, str] = {
    "math": "math",
    "mathematics": "math",
    "ela": "ela",
    "english": "ela",
    "language arts": "ela",
    "english language arts": "ela",
    "reading": "ela",
    "writing": "ela",
    "science": "science",
    "biology": "science",
    "chemistry": "science",
    "physics": "science",
    "earth science": "science",
    "history": "history",
    "social studies": "history",
    "civics": "history",
    "economics": "history",
    "geography": "history",
}


def resolve_subject(subject: str) -> Optional[str]:
    """Resolve a subject name to a canonical key in the STANDARDS dict."""
    return SUBJECT_ALIASES.get(subject.lower().strip())


def get_standards(
    subject: str,
    grade: Optional[str] = None,
) -> list[tuple[str, str, str]]:
    """Return standards matching the subject and optional grade filter.

    Args:
        subject: Subject name (will be resolved via aliases).
        grade: Grade level filter (e.g., "8", "K", "9-12"). If None, returns all.

    Returns:
        List of (code, description, grade_band) tuples.
    """
    key = resolve_subject(subject)
    if key is None:
        return []

    all_standards = STANDARDS.get(key, [])
    if grade is None:
        return all_standards

    grade = grade.strip()
    results = []
    for code, desc, band in all_standards:
        if _grade_matches(grade, band):
            results.append((code, desc, band))
    return results


def _grade_matches(query_grade: str, band: str) -> bool:
    """Check if a queried grade falls within a standard's grade band."""
    query = query_grade.upper().strip()
    band_upper = band.upper().strip()

    # Exact match
    if query == band_upper:
        return True

    # K special case
    if query == "K" and band_upper == "K":
        return True

    # Range match: "6-8", "9-12", "11-12"
    if "-" in band_upper:
        parts = band_upper.split("-")
        try:
            low = int(parts[0])
            high = int(parts[1])
            grade_num = int(query)
            return low <= grade_num <= high
        except ValueError:
            return False

    # Numeric exact match
    try:
        return int(query) == int(band_upper)
    except ValueError:
        return False
