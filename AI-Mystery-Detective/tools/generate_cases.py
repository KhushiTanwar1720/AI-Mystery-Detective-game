"""
One-time content-authoring script for AI Mystery Detective.

Generates cases/case_003.json .. case_016.json (campaign levels 2-15)
plus their cases/suspects/, cases/evidence/, cases/clues/, and
cases/locations/ files, following the exact schema/conventions
already established by case_001 ("The Missing Necklace").

This script is NOT part of the runtime game -- it is a one-time
authoring tool kept in tools/ for transparency/reproducibility. The
actual game only ever reads the generated JSON files under cases/.

Run with:
    python tools/generate_cases.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES_DIR = ROOT / "cases"


def write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


# Each entry below is one fully authored mystery: a case file, a list
# of suspects, a list of evidence, a list of clues, and a list of
# locations (with connections). IDs are namespaced per case to avoid
# collisions across the campaign (all managers are shared/global at
# runtime, so ids MUST be unique project-wide).

CASES = []

# ---------------------------------------------------------------------------
# LEVEL 2 -- "Whispers in the Old Hotel"  (case_003)
# ---------------------------------------------------------------------------
CASES.append(dict(
    case_id="case_003",
    title="Whispers in the Old Hotel",
    description=(
        "The Grand Meridian Hotel has stood empty for a decade, but its "
        "owner's estate is finally being settled. A quick inspection turns "
        "into an investigation when the wall safe in Room 207 -- said to "
        "hold the hotel's original land deed -- is found forced open and "
        "empty, and the caretaker's log ends mid-sentence."
    ),
    location="Grand Meridian Hotel",
    crime_type="theft",
    difficulty="easy",
    correct_suspect="Renee Ashworth",
    suspects=["Marcus Bell", "Renee Ashworth", "Tobias Grey", "Iris Calloway"],
    evidence=[], clues=[], status="not_started",
    _suspects=[
        dict(suspect_id="suspect_marcus_bell", name="Marcus Bell", age=44,
             occupation="Antiques dealer", description="A well-dressed dealer who has been trying to buy the hotel's fixtures for months.",
             relationship_to_victim="Prospective buyer",
             alibi="Says he was cataloguing furniture in the lobby all afternoon.",
             behavior=["Kept steering the conversation toward the value of the deed rather than the theft itself."],
             statements=[], suspicion_level=25),
        dict(suspect_id="suspect_renee_ashworth", name="Renee Ashworth", age=31,
             occupation="Niece of the estate's owner", description="Set to inherit the hotel property once probate closes -- unless the deed proves the land was never truly her uncle's to leave.",
             relationship_to_victim="Heir",
             alibi="Claims she arrived at the hotel only minutes before the safe was found empty.",
             behavior=["Her shoes were damp with basement dust despite her claiming she'd never gone downstairs."],
             statements=[], suspicion_level=40),
        dict(suspect_id="suspect_tobias_grey", name="Tobias Grey", age=58,
             occupation="Groundskeeper", description="Has maintained the property alone since it closed, resentful of never being paid for the last two years.",
             relationship_to_victim="Employee",
             alibi="Says he was clearing the garden path and never went above the ground floor.",
             behavior=["Mentioned being owed back wages before anyone asked about money."],
             statements=[], suspicion_level=20),
        dict(suspect_id="suspect_iris_calloway", name="Iris Calloway", age=63,
             occupation="Former front desk clerk", description="Returned for the first time since the hotel closed, saying she wanted to see it one last time.",
             relationship_to_victim="Former employee",
             alibi="Says she went straight to the reception desk and stayed there reminiscing.",
             behavior=["Recognized the safe's mechanism instantly, despite it being an unusual custom model."],
             statements=[], suspicion_level=15),
    ],
    _evidence=[
        dict(evidence_id="evidence_003_pry_marks", name="Fresh Pry Marks", description="Scrape marks on the safe's edge, made with a tool no more than a few days old -- not decade-old rust.", evidence_type="physical", location_found="Room 207", importance="high", discovered=False, related_suspects=["Renee Ashworth"]),
        dict(evidence_id="evidence_003_basement_dust", name="Disturbed Basement Dust", description="A single set of fresh footprints crossing a decade of undisturbed dust, leading toward the service stairwell up to Room 207.", evidence_type="physical", location_found="Basement", importance="high", discovered=False, related_suspects=["Renee Ashworth"]),
        dict(evidence_id="evidence_003_probate_letter", name="Probate Attorney's Letter", description="A letter warning that if the original deed surfaces, it names the land a public trust -- voiding Renee's inheritance entirely.", evidence_type="document", location_found="Reception", importance="critical", discovered=False, related_suspects=["Renee Ashworth"]),
        dict(evidence_id="evidence_003_caretaker_log", name="Caretaker's Log", description="Tobias's logbook, ending abruptly the same night with the line 'someone's been in Room 207 again.'", evidence_type="document", location_found="Guest Hallway", importance="medium", discovered=False, related_suspects=["Tobias Grey"]),
        dict(evidence_id="evidence_003_appraisal_note", name="Torn Appraisal Note", description="A note in Marcus Bell's handwriting estimating the hotel's fixtures at well under what he offered publicly -- he wanted it cheap, not the deed.", evidence_type="document", location_found="Room 207", importance="low", discovered=False, related_suspects=["Marcus Bell"]),
    ],
    _clues=[
        dict(clue_id="clue_003_tool_match", description="The pry marks on the safe match a flathead tool found in Renee's car, not any tool from Tobias's shed.", source="Crime scene inspection", location="Room 207", importance="critical", discovered=False, related_evidence=["evidence_003_pry_marks"], related_suspects=["Renee Ashworth"]),
        dict(clue_id="clue_003_footprint_size", description="The fresh basement footprints match Renee's shoe size, not Tobias's or Marcus's.", source="Crime scene inspection", location="Basement", importance="high", discovered=False, related_evidence=["evidence_003_basement_dust"], related_suspects=["Renee Ashworth"]),
        dict(clue_id="clue_003_motive", description="The probate letter shows Renee had every reason to make the deed disappear before the estate closes.", source="Evidence analysis", location="Reception", importance="critical", discovered=False, related_evidence=["evidence_003_probate_letter"], related_suspects=["Renee Ashworth"]),
        dict(clue_id="clue_003_contradiction", description="Renee said she never went below the ground floor, but the basement footprints and dust on her shoes say otherwise.", source="Suspect questioning", location="Basement", importance="high", discovered=False, related_evidence=["evidence_003_basement_dust"], related_suspects=["Renee Ashworth"]),
        dict(clue_id="clue_003_red_herring", description="Tobias's log entry is unsettling but only proves he noticed the intrusion, not that he caused it.", source="Evidence analysis", location="Guest Hallway", importance="low", discovered=False, related_evidence=["evidence_003_caretaker_log"], related_suspects=["Tobias Grey"]),
    ],
    _locations=[
        dict(location_id="loc_003_reception", name="Abandoned Hotel Reception", description="Dust sheets cover a once-grand lobby; the register still lies open to the last night the hotel was full.", location_type="room", connected_locations=["loc_003_hallway", "loc_003_basement"], available_evidence=["evidence_003_probate_letter"], available_clues=[]),
        dict(location_id="loc_003_hallway", name="Guest Hallway", description="A long corridor of numbered doors, most swollen shut with age.", location_type="hallway", connected_locations=["loc_003_reception", "loc_003_room207"], available_evidence=["evidence_003_caretaker_log"], available_clues=["clue_003_red_herring"]),
        dict(location_id="loc_003_room207", name="Room 207", description="The forced-open wall safe still hangs ajar behind a crooked painting.", location_type="room", connected_locations=["loc_003_hallway"], available_evidence=["evidence_003_pry_marks", "evidence_003_appraisal_note"], available_clues=["clue_003_tool_match"]),
        dict(location_id="loc_003_basement", name="Basement", description="A decade of undisturbed dust, broken only by one very recent set of footprints.", location_type="basement", connected_locations=["loc_003_reception"], available_evidence=["evidence_003_basement_dust"], available_clues=["clue_003_footprint_size", "clue_003_contradiction", "clue_003_motive"]),
    ],
))

# ---------------------------------------------------------------------------
# LEVEL 3 -- "The Empty School"  (case_004)
# ---------------------------------------------------------------------------
CASES.append(dict(
    case_id="case_004",
    title="The Empty School",
    description=(
        "Roosevelt Middle School is closed for the summer, but someone has "
        "broken into the principal's locked trophy cabinet and taken the "
        "school's century-old founder's medal -- and left the auditorium "
        "stage covered in red paint spelling out a warning to 'stay out'."
    ),
    location="Roosevelt Middle School",
    crime_type="theft",
    difficulty="easy",
    correct_suspect="Danny Ortiz",
    suspects=["Ruben Cole", "Ms. Fairweather", "Danny Ortiz", "Carla Nguyen"],
    evidence=[], clues=[], status="not_started",
    _suspects=[
        dict(suspect_id="suspect_ruben_cole", name="Ruben Cole", age=51,
             occupation="Janitor", description="Has worked at the school for twenty years and holds a master key to every room.",
             relationship_to_victim="Employee",
             alibi="Says he was mowing the athletic field the whole afternoon.",
             behavior=["Seemed more upset about the mess on stage than the missing medal."],
             statements=[], suspicion_level=15),
        dict(suspect_id="suspect_fairweather", name="Ms. Fairweather", age=37,
             occupation="Substitute teacher", description="Filled in for a semester and was recently told she would not be asked back next year.",
             relationship_to_victim="Former staff",
             alibi="Claims she only came by to collect a box of personal books from the classroom wing.",
             behavior=["Grew defensive when asked why she still had a staff key months after leaving."],
             statements=[], suspicion_level=30),
        dict(suspect_id="suspect_danny_ortiz", name="Danny Ortiz", age=17,
             occupation="Former student", description="Expelled last spring after a fight in the auditorium; still bitter about it.",
             relationship_to_victim="Former student",
             alibi="Says he was nowhere near the school today.",
             behavior=["Had red paint under his fingernails and a fresh scrape matching the cabinet's broken latch."],
             statements=[], suspicion_level=55),
        dict(suspect_id="suspect_carla_nguyen", name="Carla Nguyen", age=45,
             occupation="PTA president", description="Organizing an alumni fundraiser and had asked to borrow the medal for a display.",
             relationship_to_victim="Volunteer",
             alibi="Says she dropped off fundraiser flyers at the front office and left immediately.",
             behavior=["Was annoyed her request to display the medal had been denied by the principal."],
             statements=[], suspicion_level=20),
    ],
    _evidence=[
        dict(evidence_id="evidence_004_paint_hands", name="Red Paint Residue", description="A smear of red paint on the storage room doorknob, the same shade used on the auditorium stage.", evidence_type="physical", location_found="Storage Room", importance="high", discovered=False, related_suspects=["Danny Ortiz"]),
        dict(evidence_id="evidence_004_shoeprint", name="Muddy Shoeprint", description="A sneaker print by the broken cabinet latch, tread pattern matching a popular skate shoe.", evidence_type="physical", location_found="Principal's Office", importance="high", discovered=False, related_suspects=["Danny Ortiz"]),
        dict(evidence_id="evidence_004_expulsion_letter", name="Expulsion Letter Copy", description="A copy of Danny's expulsion letter, crumpled and stuffed behind a filing cabinet.", evidence_type="document", location_found="Principal's Office", importance="medium", discovered=False, related_suspects=["Danny Ortiz"]),
        dict(evidence_id="evidence_004_flyers", name="Fundraiser Flyers", description="A stack of flyers listing the founder's medal as the fundraiser's centerpiece attraction -- dated after the theft, not before.", evidence_type="document", location_found="Classroom Wing", importance="low", discovered=False, related_suspects=["Carla Nguyen"]),
        dict(evidence_id="evidence_004_spraycan", name="Empty Paint Can", description="An empty can of the same red paint, hidden behind a stack of stage curtains.", evidence_type="physical", location_found="Old Auditorium", importance="medium", discovered=False, related_suspects=["Danny Ortiz"]),
    ],
    _clues=[
        dict(clue_id="clue_004_latch_match", description="The scrape on the cabinet latch lines up exactly with the shoeprint's toe angle -- someone kicked it open.", source="Crime scene inspection", location="Principal's Office", importance="critical", discovered=False, related_evidence=["evidence_004_shoeprint"], related_suspects=["Danny Ortiz"]),
        dict(clue_id="clue_004_paint_trail", description="Paint residue leads in a faint trail from the auditorium stage to the storage room where the medal display case usually sits empty.", source="Crime scene inspection", location="Old Auditorium", importance="high", discovered=False, related_evidence=["evidence_004_paint_hands", "evidence_004_spraycan"], related_suspects=["Danny Ortiz"]),
        dict(clue_id="clue_004_motive", description="The expulsion letter confirms Danny was banned from campus after the same auditorium fight -- a clear grudge against the school.", source="Evidence analysis", location="Principal's Office", importance="high", discovered=False, related_evidence=["evidence_004_expulsion_letter"], related_suspects=["Danny Ortiz"]),
        dict(clue_id="clue_004_contradiction", description="Danny claimed he was nowhere near the school, but the paint under his nails is still wet.", source="Suspect questioning", location="Storage Room", importance="critical", discovered=False, related_evidence=["evidence_004_paint_hands"], related_suspects=["Danny Ortiz"]),
        dict(clue_id="clue_004_red_herring", description="Carla's flyers already advertise the medal in the display -- but they're dated the day after the theft, meaning she couldn't have known it would be missing in advance.", source="Evidence analysis", location="Classroom Wing", importance="low", discovered=False, related_evidence=["evidence_004_flyers"], related_suspects=["Carla Nguyen"]),
    ],
    _locations=[
        dict(location_id="loc_004_entrance", name="School Entrance", description="Propped open with a brick despite the school being officially closed for summer.", location_type="entrance", connected_locations=["loc_004_classrooms", "loc_004_office"], available_evidence=[], available_clues=[]),
        dict(location_id="loc_004_classrooms", name="Classroom Wing", description="Rows of empty desks under drop cloths, sunlight cutting through drawn blinds.", location_type="hallway", connected_locations=["loc_004_entrance", "loc_004_storage"], available_evidence=["evidence_004_flyers"], available_clues=["clue_004_red_herring"]),
        dict(location_id="loc_004_office", name="Principal's Office", description="The trophy cabinet stands with its glass door hanging from one hinge.", location_type="room", connected_locations=["loc_004_entrance", "loc_004_auditorium"], available_evidence=["evidence_004_shoeprint", "evidence_004_expulsion_letter"], available_clues=["clue_004_latch_match", "clue_004_motive"]),
        dict(location_id="loc_004_storage", name="Storage Room", description="Shelves of old textbooks and a display case that once held the founder's medal.", location_type="room", connected_locations=["loc_004_classrooms"], available_evidence=["evidence_004_paint_hands"], available_clues=["clue_004_contradiction"]),
        dict(location_id="loc_004_auditorium", name="Old Auditorium", description="A warning painted in red across the stage floor, still tacky to the touch.", location_type="hall", connected_locations=["loc_004_office"], available_evidence=["evidence_004_spraycan"], available_clues=["clue_004_paint_trail"]),
    ],
))

# ---------------------------------------------------------------------------
# LEVEL 4 -- "Footsteps in the Forest"  (case_005)
# ---------------------------------------------------------------------------
CASES.append(dict(
    case_id="case_005",
    title="Footsteps in the Forest",
    description=(
        "Hiker Colton Reyes never checked out of the ranger station after a "
        "solo overnight trip. His tent is found collapsed at an abandoned "
        "camp, his gear cache emptied, and a set of unfamiliar boot prints "
        "circle the site before vanishing onto hard ground near the "
        "watchtower."
    ),
    location="Whitmore National Forest",
    crime_type="disappearance",
    difficulty="medium",
    correct_suspect="Owen Pratt",
    suspects=["Silas Combe", "Owen Pratt", "Dale Whitfield", "Meredith Reyes"],
    evidence=[], clues=[], status="not_started",
    _suspects=[
        dict(suspect_id="suspect_silas_combe", name="Silas Combe", age=49,
             occupation="Park ranger", description="Has patrolled this section of the forest for fifteen years and logged Colton's permit himself.",
             relationship_to_victim="Park official",
             alibi="Says he was stationed at the ranger cabin monitoring radio checks all night.",
             behavior=["Kept checking his watch as though expecting someone."],
             statements=[], suspicion_level=15),
        dict(suspect_id="suspect_owen_pratt", name="Owen Pratt", age=39,
             occupation="Rival startup founder", description="Colton's former business partner, locked in a bitter lawsuit over a patent Colton filed first.",
             relationship_to_victim="Business rival",
             alibi="Claims he was at a hotel two hours away the entire trip.",
             behavior=["A hotel receipt he offered as proof was for the night before the disappearance, not the night of it."],
             statements=[], suspicion_level=50),
        dict(suspect_id="suspect_dale_whitfield", name="Dale Whitfield", age=33,
             occupation="Unlicensed trapper", description="Known to work this stretch of forest illegally and avoid rangers whenever possible.",
             relationship_to_victim="Stranger",
             alibi="Refuses to say exactly where he was, only that he 'wasn't near the camp.'",
             behavior=["Grew nervous discussing the watchtower specifically."],
             statements=[], suspicion_level=25),
        dict(suspect_id="suspect_meredith_reyes", name="Meredith Reyes", age=28,
             occupation="Colton's sister", description="Reported him missing after he failed to call as promised.",
             relationship_to_victim="Sibling",
             alibi="Was at home in the city, confirmed by her office's building log.",
             behavior=["Provided the most detail of anyone about Colton's exact planned route."],
             statements=[], suspicion_level=10),
    ],
    _evidence=[
        dict(evidence_id="evidence_005_bootprint", name="Unfamiliar Boot Print", description="A boot print far larger than Colton's own gear, circling the collapsed tent twice.", evidence_type="physical", location_found="Abandoned Camp", importance="high", discovered=False, related_suspects=["Owen Pratt"]),
        dict(evidence_id="evidence_005_receipt", name="Hotel Receipt", description="Owen's hotel receipt, timestamped the night before the disappearance -- leaving the actual night unaccounted for.", evidence_type="document", location_found="Ranger Cabin", importance="critical", discovered=False, related_suspects=["Owen Pratt"]),
        dict(evidence_id="evidence_005_lawsuit_papers", name="Lawsuit Papers", description="Court filings showing Owen stood to lose everything if Colton's patent priority was upheld next month.", evidence_type="document", location_found="Ranger Cabin", importance="high", discovered=False, related_suspects=["Owen Pratt"]),
        dict(evidence_id="evidence_005_cigarette", name="Crushed Cigarette Butts", description="A brand Owen is known to smoke, found at the base of the watchtower.", evidence_type="physical", location_found="Watchtower", importance="medium", discovered=False, related_suspects=["Owen Pratt"]),
        dict(evidence_id="evidence_005_snareline", name="Snare Line", description="One of Dale's illegal snare lines, strung well away from the camp itself.", evidence_type="physical", location_found="Forest Trail", importance="low", discovered=False, related_suspects=["Dale Whitfield"]),
    ],
    _clues=[
        dict(clue_id="clue_005_print_match", description="The boot print's tread matches a limited-edition hiking boot Owen was photographed wearing at a conference last month.", source="Evidence analysis", location="Abandoned Camp", importance="critical", discovered=False, related_evidence=["evidence_005_bootprint"], related_suspects=["Owen Pratt"]),
        dict(clue_id="clue_005_alibi_gap", description="The hotel receipt only covers the night before -- Owen has no account of his whereabouts during the actual disappearance.", source="Evidence analysis", location="Ranger Cabin", importance="critical", discovered=False, related_evidence=["evidence_005_receipt"], related_suspects=["Owen Pratt"]),
        dict(clue_id="clue_005_motive", description="Owen's lawsuit would collapse if Colton testified in three weeks -- disappearing him solves the case for good.", source="Evidence analysis", location="Ranger Cabin", importance="high", discovered=False, related_evidence=["evidence_005_lawsuit_papers"], related_suspects=["Owen Pratt"]),
        dict(clue_id="clue_005_watchtower_link", description="The cigarette brand at the watchtower is the same one Owen was seen smoking outside the hotel.", source="Crime scene inspection", location="Watchtower", importance="medium", discovered=False, related_evidence=["evidence_005_cigarette"], related_suspects=["Owen Pratt"]),
        dict(clue_id="clue_005_red_herring", description="Dale's snare line is illegal but far from the camp -- poaching, not the disappearance, explains his evasiveness.", source="Crime scene inspection", location="Forest Trail", importance="low", discovered=False, related_evidence=["evidence_005_snareline"], related_suspects=["Dale Whitfield"]),
    ],
    _locations=[
        dict(location_id="loc_005_trail", name="Forest Trail", description="The marked trail Colton signed out on, muddy from a recent rain.", location_type="outdoor", connected_locations=["loc_005_cabin", "loc_005_camp"], available_evidence=["evidence_005_snareline"], available_clues=["clue_005_red_herring"]),
        dict(location_id="loc_005_cabin", name="Ranger Cabin", description="Silas's small station, permit logs pinned to a corkboard.", location_type="room", connected_locations=["loc_005_trail"], available_evidence=["evidence_005_receipt", "evidence_005_lawsuit_papers"], available_clues=["clue_005_alibi_gap", "clue_005_motive"]),
        dict(location_id="loc_005_camp", name="Abandoned Camp", description="Colton's tent lies collapsed, gear scattered as though searched in a hurry.", location_type="outdoor", connected_locations=["loc_005_trail", "loc_005_watchtower"], available_evidence=["evidence_005_bootprint"], available_clues=["clue_005_print_match"]),
        dict(location_id="loc_005_watchtower", name="Watchtower", description="A rusted fire lookout tower with a clear view down onto the camp below.", location_type="outdoor", connected_locations=["loc_005_camp"], available_evidence=["evidence_005_cigarette"], available_clues=["clue_005_watchtower_link"]),
    ],
))

# ---------------------------------------------------------------------------
# LEVEL 5 -- "The House at the End of the Road"  (case_006)
# ---------------------------------------------------------------------------
CASES.append(dict(
    case_id="case_006",
    title="The House at the End of the Road",
    description=(
        "Old Mr. Calder died peacefully in his sleep, but his handwritten "
        "final will -- kept in a locked box in the attic -- is gone by the "
        "time the family lawyer arrives to read it. Without it, an older, "
        "far less generous will takes effect."
    ),
    location="The Calder House",
    crime_type="theft",
    difficulty="medium",
    correct_suspect="Warren Pike",
    suspects=["Nora Calder", "Warren Pike", "Douglas Calder", "Ellis Thorne"],
    evidence=[], clues=[], status="not_started",
    _suspects=[
        dict(suspect_id="suspect_nora_calder", name="Nora Calder", age=61,
             occupation="Longtime housekeeper", description="Cared for Mr. Calder for over twenty years and was named a beneficiary in the missing will.",
             relationship_to_victim="Caretaker",
             alibi="Says she was in the kitchen preparing for the reading of the will.",
             behavior=["Openly wept when the missing will was discovered."],
             statements=[], suspicion_level=10),
        dict(suspect_id="suspect_warren_pike", name="Warren Pike", age=54,
             occupation="Family lawyer", description="Drafted both wills and stood to earn a smaller fee -- and lose future business from the family -- under the newer, more equitable one.",
             relationship_to_victim="Attorney",
             alibi="Claims he arrived at the house only for the scheduled reading.",
             behavior=["Was unusually quick to suggest the older will simply be honored instead of searching further."],
             statements=[], suspicion_level=45),
        dict(suspect_id="suspect_douglas_calder", name="Douglas Calder", age=36,
             occupation="Estranged son", description="Cut out of the older will entirely after a falling-out, but reinstated in the newer one.",
             relationship_to_victim="Son",
             alibi="Says he only just arrived in town this morning, straight from the airport.",
             behavior=["Seemed genuinely confused rather than defensive when the will was reported missing."],
             statements=[], suspicion_level=15),
        dict(suspect_id="suspect_ellis_thorne", name="Ellis Thorne", age=42,
             occupation="Neighbor", description="A longtime friend of the family who often helped Mr. Calder with paperwork.",
             relationship_to_victim="Family friend",
             alibi="Says he stopped by yesterday to drop off groceries and hasn't been back since.",
             behavior=["Knew the exact location of the attic box without being told."],
             statements=[], suspicion_level=20),
    ],
    _evidence=[
        dict(evidence_id="evidence_006_broken_lock", name="Broken Attic Lock", description="The lockbox's lock was picked with a tool, not forced -- suggesting someone skilled or professional.", evidence_type="physical", location_found="Attic", importance="high", discovered=False, related_suspects=["Warren Pike"]),
        dict(evidence_id="evidence_006_fee_letter", name="Fee Schedule Letter", description="A letter showing Warren's fee under the new will is less than a third of what the old will guarantees him as executor.", evidence_type="document", location_found="Locked Study", importance="critical", discovered=False, related_suspects=["Warren Pike"]),
        dict(evidence_id="evidence_006_briefcase_key", name="Spare Attic Key", description="A spare attic key found tucked in Warren's briefcase, which he claimed he'd never used.", evidence_type="physical", location_found="Living Room", importance="high", discovered=False, related_suspects=["Warren Pike"]),
        dict(evidence_id="evidence_006_garden_soil", name="Disturbed Garden Soil", description="A small patch of freshly turned soil near the garden shed, oddly out of place.", evidence_type="physical", location_found="Garden", importance="low", discovered=False, related_suspects=["Ellis Thorne"]),
        dict(evidence_id="evidence_006_old_draft", name="Old Will Draft", description="An early draft of the newer will with Warren's handwritten margin notes complaining about its terms.", evidence_type="document", location_found="Locked Study", importance="medium", discovered=False, related_suspects=["Warren Pike"]),
    ],
    _clues=[
        dict(clue_id="clue_006_lockpick_skill", description="The picked lock requires legal-document-box expertise -- exactly the kind of lock Warren's own office uses.", source="Crime scene inspection", location="Attic", importance="high", discovered=False, related_evidence=["evidence_006_broken_lock"], related_suspects=["Warren Pike"]),
        dict(clue_id="clue_006_motive", description="The fee schedule gives Warren a direct financial reason to make the new will disappear.", source="Evidence analysis", location="Locked Study", importance="critical", discovered=False, related_evidence=["evidence_006_fee_letter"], related_suspects=["Warren Pike"]),
        dict(clue_id="clue_006_key_contradiction", description="Warren denied ever using the attic, but a spare key to it was in his own briefcase.", source="Suspect questioning", location="Living Room", importance="critical", discovered=False, related_evidence=["evidence_006_briefcase_key"], related_suspects=["Warren Pike"]),
        dict(clue_id="clue_006_annotations", description="Warren's own handwriting shows he resented the new will's terms weeks before Mr. Calder died.", source="Evidence analysis", location="Locked Study", importance="medium", discovered=False, related_evidence=["evidence_006_old_draft"], related_suspects=["Warren Pike"]),
        dict(clue_id="clue_006_red_herring", description="The disturbed soil turns out to be from Ellis planting bulbs for Mr. Calder days before he died -- unrelated to the theft.", source="Crime scene inspection", location="Garden", importance="low", discovered=False, related_evidence=["evidence_006_garden_soil"], related_suspects=["Ellis Thorne"]),
    ],
    _locations=[
        dict(location_id="loc_006_hall", name="Front Hall", description="A grandfather clock ticks in the entryway, the house unnervingly quiet.", location_type="room", connected_locations=["loc_006_living", "loc_006_garden"], available_evidence=[], available_clues=[]),
        dict(location_id="loc_006_living", name="Living Room", description="Family photos line the mantel above a cold fireplace.", location_type="room", connected_locations=["loc_006_hall", "loc_006_attic", "loc_006_study"], available_evidence=["evidence_006_briefcase_key"], available_clues=["clue_006_key_contradiction"]),
        dict(location_id="loc_006_attic", name="Attic", description="Boxes of old belongings surround the empty, splintered lockbox.", location_type="room", connected_locations=["loc_006_living"], available_evidence=["evidence_006_broken_lock"], available_clues=["clue_006_lockpick_skill"]),
        dict(location_id="loc_006_study", name="Locked Study", description="Mr. Calder's private study, still smelling faintly of pipe tobacco.", location_type="room", connected_locations=["loc_006_living"], available_evidence=["evidence_006_fee_letter", "evidence_006_old_draft"], available_clues=["clue_006_motive", "clue_006_annotations"]),
        dict(location_id="loc_006_garden", name="Garden", description="A modest garden, recently tended despite the household's grief.", location_type="outdoor", connected_locations=["loc_006_hall"], available_evidence=["evidence_006_garden_soil"], available_clues=["clue_006_red_herring"]),
    ],
))

# ---------------------------------------------------------------------------
# LEVEL 6 -- "The Silent Hospital"  (case_007)
# ---------------------------------------------------------------------------
CASES.append(dict(
    case_id="case_007",
    title="The Silent Hospital",
    description=(
        "St. Agnes Hospital shut its doors after a malpractice scandal "
        "twenty years ago. A journalist researching the case is found "
        "unconscious in the records room, and the patient file at the "
        "center of the old scandal has vanished from a cabinet that was "
        "supposedly welded shut."
    ),
    location="St. Agnes Hospital",
    crime_type="document theft",
    difficulty="medium",
    correct_suspect="Dr. Warren Holt",
    suspects=["Dr. Warren Holt", "Nathaniel Cross", "Priya Desai", "Sam the Security Guard"],
    evidence=[], clues=[], status="not_started",
    _suspects=[
        dict(suspect_id="suspect_warren_holt", name="Dr. Warren Holt", age=67,
             occupation="Former hospital administrator", description="Ran St. Agnes when the malpractice scandal broke and has always denied personal responsibility.",
             relationship_to_victim="Former colleague of the journalist's source",
             alibi="Says he hasn't set foot in the hospital in fifteen years.",
             behavior=["Knew the records room's exact layout despite claiming not to have been inside in over a decade."],
             statements=[], suspicion_level=50),
        dict(suspect_id="suspect_nathaniel_cross", name="Nathaniel Cross", age=40,
             occupation="Investigative journalist", description="The one found unconscious -- now also a person of interest, since head injuries from a fall can look identical to an attack.",
             relationship_to_victim="Self",
             alibi="Has no memory of the incident itself.",
             behavior=["Was adamant the missing file, not his own safety, be the priority."],
             statements=[], suspicion_level=10),
        dict(suspect_id="suspect_priya_desai", name="Priya Desai", age=29,
             occupation="Nathaniel's research assistant", description="Helped compile years of research into the scandal and knew exactly which file mattered most.",
             relationship_to_victim="Colleague",
             alibi="Says she was waiting in the car the whole time.",
             behavior=["Grew agitated when asked why she never came inside to check on him."],
             statements=[], suspicion_level=25),
        dict(suspect_id="suspect_sam_guard", name="Sam the Security Guard", age=52,
             occupation="Overnight security contractor", description="Hired to guard the condemned building against trespassers.",
             relationship_to_victim="Stranger",
             alibi="Says he was doing his usual rounds and heard nothing unusual.",
             behavior=["His flashlight batteries were dead when checked, despite him claiming to have used it all night."],
             statements=[], suspicion_level=15),
    ],
    _evidence=[
        dict(evidence_id="evidence_007_cut_weld", name="Freshly Cut Weld", description="The 'welded shut' cabinet's seam was cut with a tool, cleanly and recently, not decades ago.", evidence_type="physical", location_found="Records Room", importance="critical", discovered=False, related_suspects=["Dr. Warren Holt"]),
        dict(evidence_id="evidence_007_settlement", name="Sealed Settlement Copy", description="A copy of a confidential settlement that names Dr. Holt as personally negligent -- the exact contents of the missing file, according to Nathaniel's notes.", evidence_type="document", location_found="Reception", importance="critical", discovered=False, related_suspects=["Dr. Warren Holt"]),
        dict(evidence_id="evidence_007_glove", name="Surgical Glove", description="A single latex glove dropped near where Nathaniel was found, a brand still used at Dr. Holt's current private practice.", evidence_type="physical", location_found="Records Room", importance="high", discovered=False, related_suspects=["Dr. Warren Holt"]),
        dict(evidence_id="evidence_007_visitor_log", name="Dusty Visitor Log", description="An old sign-in sheet with one very recent entry, the ink still legible where every other line has faded.", evidence_type="document", location_found="Patient Ward", importance="medium", discovered=False, related_suspects=["Dr. Warren Holt"]),
        dict(evidence_id="evidence_007_flashlight", name="Guard's Flashlight", description="Sam's flashlight, batteries fully dead.", evidence_type="physical", location_found="Basement", importance="low", discovered=False, related_suspects=["Sam the Security Guard"]),
    ],
    _clues=[
        dict(clue_id="clue_007_weld_timing", description="A cut this clean and recent means someone entered the cabinet within the last few days, not years ago.", source="Crime scene inspection", location="Records Room", importance="critical", discovered=False, related_evidence=["evidence_007_cut_weld"], related_suspects=["Dr. Warren Holt"]),
        dict(clue_id="clue_007_motive", description="The settlement copy shows exactly what Dr. Holt had to lose if the original file ever surfaced publicly.", source="Evidence analysis", location="Reception", importance="critical", discovered=False, related_evidence=["evidence_007_settlement"], related_suspects=["Dr. Warren Holt"]),
        dict(clue_id="clue_007_glove_brand", description="The glove brand is only distributed to Dr. Holt's current clinic, not sold to the public.", source="Evidence analysis", location="Records Room", importance="high", discovered=False, related_evidence=["evidence_007_glove"], related_suspects=["Dr. Warren Holt"]),
        dict(clue_id="clue_007_contradiction", description="Dr. Holt said he hasn't entered the hospital in fifteen years, but the visitor log's freshest entry has his handwriting.", source="Suspect questioning", location="Patient Ward", importance="critical", discovered=False, related_evidence=["evidence_007_visitor_log"], related_suspects=["Dr. Warren Holt"]),
        dict(clue_id="clue_007_red_herring", description="Sam's dead flashlight only proves poor equipment maintenance, not involvement -- his rounds route never passed the records room.", source="Crime scene inspection", location="Basement", importance="low", discovered=False, related_evidence=["evidence_007_flashlight"], related_suspects=["Sam the Security Guard"]),
    ],
    _locations=[
        dict(location_id="loc_007_reception", name="Reception", description="Peeling paint and an old admissions desk, papers scattered by decades of drafts.", location_type="room", connected_locations=["loc_007_ward", "loc_007_records"], available_evidence=["evidence_007_settlement"], available_clues=["clue_007_motive"]),
        dict(location_id="loc_007_ward", name="Patient Ward", description="Rows of rusted bed frames, one visitor log still resting on a nurse's station.", location_type="room", connected_locations=["loc_007_reception", "loc_007_operating"], available_evidence=["evidence_007_visitor_log"], available_clues=["clue_007_contradiction"]),
        dict(location_id="loc_007_records", name="Records Room", description="Filing cabinets line every wall; one stands open where it should have been sealed forever.", location_type="room", connected_locations=["loc_007_reception", "loc_007_basement"], available_evidence=["evidence_007_cut_weld", "evidence_007_glove"], available_clues=["clue_007_weld_timing", "clue_007_glove_brand"]),
        dict(location_id="loc_007_operating", name="Operating Wing", description="Surgical lights hang dark and dust-covered over an empty table.", location_type="room", connected_locations=["loc_007_ward"], available_evidence=[], available_clues=[]),
        dict(location_id="loc_007_basement", name="Basement", description="Pipes drip steadily into puddles that have collected for years.", location_type="basement", connected_locations=["loc_007_records"], available_evidence=["evidence_007_flashlight"], available_clues=["clue_007_red_herring"]),
    ],
))

# ---------------------------------------------------------------------------
# LEVEL 7 -- "The Forgotten Asylum"  (case_008)
# ---------------------------------------------------------------------------
CASES.append(dict(
    case_id="case_008",
    title="The Forgotten Asylum",
    description=(
        "Blackgate Asylum closed in disgrace after reports of unauthorized "
        "experiments on patients. A historian cataloguing the site for a "
        "museum exhibit has gone silent mid-survey, and the asylum's most "
        "damning archive box -- documenting exactly who authorized the "
        "experiments -- is missing from the archive shelf."
    ),
    location="Blackgate Asylum",
    crime_type="disappearance",
    difficulty="hard",
    correct_suspect="Vivian Ashgrove",
    suspects=["Vivian Ashgrove", "Pete Malone", "Dr. Corwin Blake", "Femi Adeyemi"],
    evidence=[], clues=[], status="not_started",
    _suspects=[
        dict(suspect_id="suspect_vivian_ashgrove", name="Vivian Ashgrove", age=52,
             occupation="Descendant of the asylum's former director", description="Her grandfather authorized the experiments; she has spent years quietly buying up documents that connect her family to them.",
             relationship_to_victim="Family connection to the case",
             alibi="Claims she came only to 'pay respects' to a difficult family history.",
             behavior=["Asked pointed questions about exactly which documents the historian had already photographed."],
             statements=[], suspicion_level=55),
        dict(suspect_id="suspect_pete_malone", name="Pete Malone", age=26,
             occupation="Urban explorer", description="Frequently trespasses at the asylum to film content, well known to local authorities.",
             relationship_to_victim="Stranger",
             alibi="Says he was filming in the treatment wing the whole time and never went near the archive.",
             behavior=["Was oddly cooperative and eager to hand over his camera footage unprompted."],
             statements=[], suspicion_level=15),
        dict(suspect_id="suspect_corwin_blake", name="Dr. Corwin Blake", age=71,
             occupation="Retired psychiatrist", description="Worked briefly at the asylum decades ago and has publicly criticized its practices ever since.",
             relationship_to_victim="Former colleague",
             alibi="Says he was at the site to be interviewed by the historian, as scheduled.",
             behavior=["Provided detailed, unprompted corroboration of the historian's version of events."],
             statements=[], suspicion_level=10),
        dict(suspect_id="suspect_femi_adeyemi", name="Femi Adeyemi", age=34,
             occupation="Museum exhibit coordinator", description="Hired the historian and stands to lose the exhibit's funding if the centerpiece documents don't surface.",
             relationship_to_victim="Employer",
             alibi="Says she was coordinating logistics by phone from outside the gate.",
             behavior=["Pushed hard to keep the investigation quiet to protect the museum's reputation."],
             statements=[], suspicion_level=20),
    ],
    _evidence=[
        dict(evidence_id="evidence_008_archive_gap", name="Empty Archive Slot", description="A single archive box missing from an otherwise untouched shelf, its neighbors undisturbed.", evidence_type="physical", location_found="Archive", importance="high", discovered=False, related_suspects=["Vivian Ashgrove"]),
        dict(evidence_id="evidence_008_family_letters", name="Family Letters", description="Personal letters showing Vivian has spent three years and considerable money buying up records connected to her grandfather's tenure.", evidence_type="document", location_found="Main Hall", importance="critical", discovered=False, related_suspects=["Vivian Ashgrove"]),
        dict(evidence_id="evidence_008_torn_ledger", name="Torn Ledger Page", description="A torn page from the historian's own research ledger, the missing corner found snagged on a shelf in the archive.", evidence_type="document", location_found="Archive", importance="high", discovered=False, related_suspects=["Vivian Ashgrove"]),
        dict(evidence_id="evidence_008_glove_print", name="Glove Print in Dust", description="A gloved handprint on the archive shelf, at a height matching Vivian, not the shorter historian.", evidence_type="physical", location_found="Archive", importance="medium", discovered=False, related_suspects=["Vivian Ashgrove"]),
        dict(evidence_id="evidence_008_camera_footage", name="Pete's Camera Footage", description="Timestamped footage confirming Pete was filming in the treatment wing during the entire window in question.", evidence_type="digital", location_found="Treatment Wing", importance="low", discovered=False, related_suspects=["Pete Malone"]),
    ],
    _clues=[
        dict(clue_id="clue_008_targeted_theft", description="Only the one box connected to Vivian's grandfather is missing -- a targeted theft, not a random one.", source="Crime scene inspection", location="Archive", importance="critical", discovered=False, related_evidence=["evidence_008_archive_gap"], related_suspects=["Vivian Ashgrove"]),
        dict(clue_id="clue_008_motive", description="The family letters show a clear, years-long motive to erase this specific documentation.", source="Evidence analysis", location="Main Hall", importance="critical", discovered=False, related_evidence=["evidence_008_family_letters"], related_suspects=["Vivian Ashgrove"]),
        dict(clue_id="clue_008_ledger_match", description="The torn ledger corner in the archive matches the historian's notebook exactly -- someone grabbed the box while he was mid-photograph.", source="Evidence analysis", location="Archive", importance="high", discovered=False, related_evidence=["evidence_008_torn_ledger"], related_suspects=["Vivian Ashgrove"]),
        dict(clue_id="clue_008_height_match", description="The glove print's height rules out the historian entirely and matches Vivian's build.", source="Crime scene inspection", location="Archive", importance="high", discovered=False, related_evidence=["evidence_008_glove_print"], related_suspects=["Vivian Ashgrove"]),
        dict(clue_id="clue_008_red_herring", description="Pete's own footage clears him -- unsettling as his hobby is, he was nowhere near the archive.", source="Evidence analysis", location="Treatment Wing", importance="low", discovered=False, related_evidence=["evidence_008_camera_footage"], related_suspects=["Pete Malone"]),
    ],
    _locations=[
        dict(location_id="loc_008_main_hall", name="Main Hall", description="A grand, decaying entrance hall, portraits of long-dead directors watching from the walls.", location_type="hall", connected_locations=["loc_008_observation", "loc_008_archive"], available_evidence=["evidence_008_family_letters"], available_clues=["clue_008_motive"]),
        dict(location_id="loc_008_observation", name="Observation Room", description="A one-way mirror still intact, facing an empty patient cell.", location_type="room", connected_locations=["loc_008_main_hall", "loc_008_treatment"], available_evidence=[], available_clues=[]),
        dict(location_id="loc_008_archive", name="Archive", description="Rows of records boxes, one slot conspicuously and precisely empty.", location_type="room", connected_locations=["loc_008_main_hall", "loc_008_underground"], available_evidence=["evidence_008_archive_gap", "evidence_008_torn_ledger", "evidence_008_glove_print"], available_clues=["clue_008_targeted_theft", "clue_008_ledger_match", "clue_008_height_match"]),
        dict(location_id="loc_008_treatment", name="Treatment Wing", description="Rusted equipment still bolted to the floor of a room no one likes to linger in.", location_type="room", connected_locations=["loc_008_observation"], available_evidence=["evidence_008_camera_footage"], available_clues=["clue_008_red_herring"]),
        dict(location_id="loc_008_underground", name="Underground Passage", description="A narrow service tunnel connecting the archive to the grounds outside, unlocked from the inside.", location_type="tunnel", connected_locations=["loc_008_archive"], available_evidence=[], available_clues=[]),
    ],
))

# ---------------------------------------------------------------------------
# LEVEL 8 -- "The Underground Station"  (case_009)
# ---------------------------------------------------------------------------
CASES.append(dict(
    case_id="case_009",
    title="The Underground Station",
    description=(
        "Millbrook Station was sealed after the transit line closed thirty "
        "years ago, its platform mural left untouched -- until a scheduled "
        "inspection finds a section of the mural cut clean out of the wall "
        "and the control room's old logbook rifled through."
    ),
    location="Millbrook Underground Station",
    crime_type="theft",
    difficulty="hard",
    correct_suspect="Corinne Vasquez",
    suspects=["Corinne Vasquez", "Harold Been", "Talia Okafor", "Gus Prentice"],
    evidence=[], clues=[], status="not_started",
    _suspects=[
        dict(suspect_id="suspect_corinne_vasquez", name="Corinne Vasquez", age=45,
             occupation="Art collector's agent", description="Represents a private collector known to pursue rare transit-era murals through any means necessary.",
             relationship_to_victim="Prospective buyer's representative",
             alibi="Claims she only toured the station on an approved historical visit.",
             behavior=["Carried a rolled canvas tube far too large for 'just paperwork.'"],
             statements=[], suspicion_level=50),
        dict(suspect_id="suspect_harold_been", name="Harold Been", age=60,
             occupation="Former station manager", description="Managed Millbrook until it closed and still keeps a spare set of keys 'for sentimental reasons.'",
             relationship_to_victim="Former employee",
             alibi="Says he stopped by only to check on the old fixtures.",
             behavior=["Grew defensive about still possessing station keys decades after being let go."],
             statements=[], suspicion_level=20),
        dict(suspect_id="suspect_talia_okafor", name="Talia Okafor", age=31,
             occupation="Transit historian", description="Has campaigned for years to have the mural preserved and displayed publicly.",
             relationship_to_victim="Advocate",
             alibi="Says she was cataloguing the platform's tile work the entire visit.",
             behavior=["Was visibly devastated, not evasive, when the missing section was found."],
             statements=[], suspicion_level=10),
        dict(suspect_id="suspect_gus_prentice", name="Gus Prentice", age=38,
             occupation="Salvage contractor", description="Hired to assess the station's fixtures for a possible redevelopment sale.",
             relationship_to_victim="Contractor",
             alibi="Says he was measuring the maintenance tunnel for the entire inspection.",
             behavior=["Kept mentioning the mural's resale value unprompted."],
             statements=[], suspicion_level=25),
    ],
    _evidence=[
        dict(evidence_id="evidence_009_cut_mural", name="Cleanly Cut Mural Section", description="A section of tile cut with precision tools, not smashed or forced -- professional work.", evidence_type="physical", location_found="Platform", importance="high", discovered=False, related_suspects=["Corinne Vasquez"]),
        dict(evidence_id="evidence_009_canvas_tube", name="Canvas Transport Tube", description="A padded tube exactly the right size for a rolled section of tile mural, found in Corinne's bag.", evidence_type="physical", location_found="Station Entrance", importance="critical", discovered=False, related_suspects=["Corinne Vasquez"]),
        dict(evidence_id="evidence_009_commission_email", name="Printed Commission Email", description="A printed email instructing Corinne to 'acquire the Millbrook piece by any means, client is paying premium.'", evidence_type="document", location_found="Control Room", importance="critical", discovered=False, related_suspects=["Corinne Vasquez"]),
        dict(evidence_id="evidence_009_toolmarks", name="Precision Cutting Tool Marks", description="Marks matching a specialty tile saw, a tool no station maintenance crew would have owned.", evidence_type="physical", location_found="Platform", importance="medium", discovered=False, related_suspects=["Corinne Vasquez"]),
        dict(evidence_id="evidence_009_logbook", name="Rifled Logbook", description="The old station logbook, pages flipped through recently looking for the mural's original placement records.", evidence_type="document", location_found="Control Room", importance="low", discovered=False, related_suspects=["Harold Been"]),
    ],
    _clues=[
        dict(clue_id="clue_009_pro_cut", description="The cut is too precise for casual vandalism -- it required specialized equipment and expertise.", source="Crime scene inspection", location="Platform", importance="high", discovered=False, related_evidence=["evidence_009_cut_mural", "evidence_009_toolmarks"], related_suspects=["Corinne Vasquez"]),
        dict(clue_id="clue_009_tube_match", description="The canvas tube is sized exactly for the missing mural section -- not incidental packing material.", source="Crime scene inspection", location="Station Entrance", importance="critical", discovered=False, related_evidence=["evidence_009_canvas_tube"], related_suspects=["Corinne Vasquez"]),
        dict(clue_id="clue_009_motive", description="The commission email proves Corinne was explicitly hired to obtain this exact piece.", source="Evidence analysis", location="Control Room", importance="critical", discovered=False, related_evidence=["evidence_009_commission_email"], related_suspects=["Corinne Vasquez"]),
        dict(clue_id="clue_009_contradiction", description="Corinne claimed her visit was purely historical, yet she carried professional cutting equipment and a transport tube.", source="Suspect questioning", location="Platform", importance="high", discovered=False, related_evidence=["evidence_009_toolmarks"], related_suspects=["Corinne Vasquez"]),
        dict(clue_id="clue_009_red_herring", description="Harold's logbook search was about a pension dispute over his old employment dates, unrelated to the mural.", source="Evidence analysis", location="Control Room", importance="low", discovered=False, related_evidence=["evidence_009_logbook"], related_suspects=["Harold Been"]),
    ],
    _locations=[
        dict(location_id="loc_009_entrance", name="Station Entrance", description="A rusted turnstile gate, propped open for the inspection team.", location_type="entrance", connected_locations=["loc_009_platform"], available_evidence=["evidence_009_canvas_tube"], available_clues=["clue_009_tube_match"]),
        dict(location_id="loc_009_platform", name="Platform", description="The famous transit mural stretches down the wall -- save for one conspicuous missing section.", location_type="room", connected_locations=["loc_009_entrance", "loc_009_control"], available_evidence=["evidence_009_cut_mural", "evidence_009_toolmarks"], available_clues=["clue_009_pro_cut", "clue_009_contradiction"]),
        dict(location_id="loc_009_control", name="Control Room", description="Dusty switchboards and an old logbook, undisturbed for decades until now.", location_type="room", connected_locations=["loc_009_platform", "loc_009_tunnel"], available_evidence=["evidence_009_commission_email", "evidence_009_logbook"], available_clues=["clue_009_motive", "clue_009_red_herring"]),
        dict(location_id="loc_009_tunnel", name="Maintenance Tunnel", description="A narrow service tunnel running parallel to the old tracks.", location_type="tunnel", connected_locations=["loc_009_control", "loc_009_office"], available_evidence=[], available_clues=[]),
        dict(location_id="loc_009_office", name="Restricted Office", description="A locked office once used by station security, its lock recently oiled.", location_type="room", connected_locations=["loc_009_tunnel"], available_evidence=[], available_clues=[]),
    ],
))

# ---------------------------------------------------------------------------
# LEVEL 9 -- "The Village That Sleeps"  (case_010)
# ---------------------------------------------------------------------------
CASES.append(dict(
    case_id="case_010",
    title="The Village That Sleeps",
    description=(
        "Every resident of Hollow Fen evacuated overnight ahead of a storm "
        "that never came. When they return, the church's centuries-old "
        "bronze bell is gone from its tower, and elderly resident Agnes "
        "Marrow -- who refused to leave -- cannot be found anywhere in the "
        "village."
    ),
    location="Hollow Fen Village",
    crime_type="theft",
    difficulty="hard",
    correct_suspect="Silas Quill",
    suspects=["Silas Quill", "Rowan Marrow", "Old Ezra", "Father Devlin"],
    evidence=[], clues=[], status="not_started",
    _suspects=[
        dict(suspect_id="suspect_silas_quill", name="Silas Quill", age=48,
             occupation="Traveling antiques trader", description="Arrived in the village the week before the evacuation, asking questions about the bell's history and value.",
             relationship_to_victim="Stranger",
             alibi="Claims he left the area before the evacuation even began.",
             behavior=["A toll receipt he offered as proof of leaving early was actually stamped hours after the evacuation started."],
             statements=[], suspicion_level=55),
        dict(suspect_id="suspect_rowan_marrow", name="Rowan Marrow", age=26,
             occupation="Agnes's grandson", description="Stands to inherit Agnes's cottage and land, and had argued with her the week before about selling the property.",
             relationship_to_victim="Grandson",
             alibi="Says he evacuated with everyone else and never went back for her.",
             behavior=["Was the only villager who refused to help search when the group returned."],
             statements=[], suspicion_level=25),
        dict(suspect_id="suspect_old_ezra", name="Old Ezra", age=74,
             occupation="Village recluse", description="Lives at the edge of the forest path and rarely speaks to anyone.",
             relationship_to_victim="Neighbor",
             alibi="Says he never evacuated at all and simply stayed in his own house the whole time.",
             behavior=["Knew Agnes had stayed behind, information no one else had shared publicly."],
             statements=[], suspicion_level=15),
        dict(suspect_id="suspect_father_devlin", name="Father Devlin", age=57,
             occupation="Church caretaker", description="Has cared for the church and its bell for thirty years.",
             relationship_to_victim="Community elder",
             alibi="Says he oversaw the evacuation and left last, locking the church behind him.",
             behavior=["Was the most distressed of anyone over the bell, insisting it be found before Agnes was even mentioned."],
             statements=[], suspicion_level=10),
    ],
    _evidence=[
        dict(evidence_id="evidence_010_toll_receipt", name="Falsified Toll Receipt", description="A toll booth receipt Silas offered as an alibi, stamped hours after the evacuation actually began -- not before.", evidence_type="document", location_found="Village Square", importance="critical", discovered=False, related_suspects=["Silas Quill"]),
        dict(evidence_id="evidence_010_rope_marks", name="Fresh Rope Marks", description="Rope abrasions on the bell tower's window ledge, consistent with lowering something heavy down by pulley.", evidence_type="physical", location_found="Abandoned Church", importance="high", discovered=False, related_suspects=["Silas Quill"]),
        dict(evidence_id="evidence_010_appraisal_card", name="Appraiser's Business Card", description="Silas's business card, found tucked behind a hymnal, listing his specialty as 'rare bronze and church artifacts.'", evidence_type="document", location_found="Abandoned Church", importance="medium", discovered=False, related_suspects=["Silas Quill"]),
        dict(evidence_id="evidence_010_wheel_tracks", name="Cart Wheel Tracks", description="Deep wheel ruts leading from the church toward the forest path -- consistent with hauling something heavy, not a person.", evidence_type="physical", location_found="Forest Path", importance="high", discovered=False, related_suspects=["Silas Quill"]),
        dict(evidence_id="evidence_010_agnes_shawl", name="Agnes's Shawl", description="Agnes's shawl, found snagged on the well's stone rim -- she'd gone to check the well herself, not been taken.", evidence_type="physical", location_found="Well Area", importance="critical", discovered=False, related_suspects=[]),
    ],
    _clues=[
        dict(clue_id="clue_010_receipt_timing", description="The toll receipt's timestamp places Silas still in the area well after he claimed to have left.", source="Evidence analysis", location="Village Square", importance="critical", discovered=False, related_evidence=["evidence_010_toll_receipt"], related_suspects=["Silas Quill"]),
        dict(clue_id="clue_010_pulley_method", description="The rope marks show exactly how a single person could lower the heavy bell without help.", source="Crime scene inspection", location="Abandoned Church", importance="high", discovered=False, related_evidence=["evidence_010_rope_marks"], related_suspects=["Silas Quill"]),
        dict(clue_id="clue_010_specialty_match", description="Silas's business card confirms his exact trade specialty matches the stolen item precisely.", source="Evidence analysis", location="Abandoned Church", importance="high", discovered=False, related_evidence=["evidence_010_appraisal_card"], related_suspects=["Silas Quill"]),
        dict(clue_id="clue_010_wheel_direction", description="The wheel tracks lead away from the village toward the main road, not toward any resident's house.", source="Crime scene inspection", location="Forest Path", importance="high", discovered=False, related_evidence=["evidence_010_wheel_tracks"], related_suspects=["Silas Quill"]),
        dict(clue_id="clue_010_agnes_resolution", description="Agnes's shawl at the well, not the forest path, shows she simply went to check on her property alone and lost track of time -- unrelated to the theft.", source="Crime scene inspection", location="Well Area", importance="medium", discovered=False, related_evidence=["evidence_010_agnes_shawl"], related_suspects=[]),
    ],
    _locations=[
        dict(location_id="loc_010_square", name="Village Square", description="Empty market stalls, the storm that never arrived leaving only an eerie stillness.", location_type="outdoor", connected_locations=["loc_010_church", "loc_010_house"], available_evidence=["evidence_010_toll_receipt"], available_clues=["clue_010_receipt_timing"]),
        dict(location_id="loc_010_church", name="Abandoned Church", description="The bell tower stands silent, its rope swinging loose where the bell should hang.", location_type="room", connected_locations=["loc_010_square"], available_evidence=["evidence_010_rope_marks", "evidence_010_appraisal_card"], available_clues=["clue_010_pulley_method", "clue_010_specialty_match"]),
        dict(location_id="loc_010_house", name="Old House", description="Agnes's cottage, door left open, kettle still on the stove.", location_type="room", connected_locations=["loc_010_square", "loc_010_well"], available_evidence=[], available_clues=[]),
        dict(location_id="loc_010_forest_path", name="Forest Path", description="A narrow dirt track leading out toward the main road, deep ruts pressed into the mud.", location_type="outdoor", connected_locations=["loc_010_well"], available_evidence=["evidence_010_wheel_tracks"], available_clues=["clue_010_wheel_direction"]),
        dict(location_id="loc_010_well", name="Well Area", description="An old stone well behind Agnes's cottage, its rim damp with recent handprints.", location_type="outdoor", connected_locations=["loc_010_house", "loc_010_forest_path"], available_evidence=["evidence_010_agnes_shawl"], available_clues=["clue_010_agnes_resolution"]),
    ],
))

# ---------------------------------------------------------------------------
# LEVEL 10 -- "The Lighthouse"  (case_011)
# ---------------------------------------------------------------------------
CASES.append(dict(
    case_id="case_011",
    title="The Lighthouse",
    description=(
        "Keeper Aldous Finch vanished during a storm, and the lighthouse's "
        "lamp mechanism was found sabotaged, dark for the first time in "
        "sixty years. Aldous's logbook -- which recorded every ship that "
        "passed -- is missing along with him."
    ),
    location="Cormorant Point Lighthouse",
    crime_type="sabotage",
    difficulty="hard",
    correct_suspect="Barnaby Slate",
    suspects=["Barnaby Slate", "Wren", "Insurance Investigator Colby", "Hugh Finch"],
    evidence=[], clues=[], status="not_started",
    _suspects=[
        dict(suspect_id="suspect_barnaby_slate", name="Barnaby Slate", age=43,
             occupation="Boat captain", description="Runs unmarked night shipments along the coast and needed the light dark for one particular crossing.",
             relationship_to_victim="Local sailor",
             alibi="Claims he was docked at a neighboring harbor the entire night of the storm.",
             behavior=["A harbor log he cited as his alibi shows his boat departing, not arriving, that night."],
             statements=[], suspicion_level=55),
        dict(suspect_id="suspect_wren", name="Wren", age=24,
             occupation="Keeper's apprentice", description="Trained under Aldous for two years and was due to take over the post next season.",
             relationship_to_victim="Apprentice",
             alibi="Says she was in the keeper's room asleep when the storm hit.",
             behavior=["Was the one who raised the alarm the moment the light went dark."],
             statements=[], suspicion_level=10),
        dict(suspect_id="suspect_colby", name="Insurance Investigator Colby", age=39,
             occupation="Maritime insurance investigator", description="Arrived to assess a separate shipping claim just before Aldous disappeared.",
             relationship_to_victim="Professional contact",
             alibi="Says he was reviewing paperwork in the basement archive all night.",
             behavior=["Asked unusually specific questions about the lamp mechanism's exact failure point."],
             statements=[], suspicion_level=20),
        dict(suspect_id="suspect_hugh_finch", name="Hugh Finch", age=51,
             occupation="Aldous's estranged brother", description="Hadn't spoken to Aldous in a decade after a dispute over their late father's boat.",
             relationship_to_victim="Sibling",
             alibi="Says he wasn't even in town during the storm.",
             behavior=["Seemed more relieved than worried when Aldous couldn't be found."],
             statements=[], suspicion_level=15),
    ],
    _evidence=[
        dict(evidence_id="evidence_011_cut_wires", name="Deliberately Cut Wires", description="The lamp mechanism's wiring was cut cleanly, not damaged by storm weather.", evidence_type="physical", location_found="Lantern Room", importance="high", discovered=False, related_suspects=["Barnaby Slate"]),
        dict(evidence_id="evidence_011_harbor_log", name="Neighboring Harbor Log", description="A harbor logbook showing Barnaby's boat departed, not stayed docked, during the exact hours in question.", evidence_type="document", location_found="Basement", importance="critical", discovered=False, related_suspects=["Barnaby Slate"]),
        dict(evidence_id="evidence_011_shipping_manifest", name="Unmarked Shipping Manifest", description="A manifest for an unregistered night crossing, timed for the same storm, found stuffed behind a shelf.", evidence_type="document", location_found="Keeper's Room", importance="critical", discovered=False, related_suspects=["Barnaby Slate"]),
        dict(evidence_id="evidence_011_wet_bootprints", name="Wet Boot Prints", description="Salt-water boot prints leading up the spiral staircase, drying at exactly the time the light failed.", evidence_type="physical", location_found="Spiral Staircase", importance="medium", discovered=False, related_suspects=["Barnaby Slate"]),
        dict(evidence_id="evidence_011_torn_logpage", name="Torn Logbook Page", description="A single torn page from Aldous's own logbook, snagged on the lantern room's railing -- he saw something and tried to record it.", evidence_type="document", location_found="Lantern Room", importance="high", discovered=False, related_suspects=[]),
    ],
    _clues=[
        dict(clue_id="clue_011_sabotage_confirmed", description="Clean-cut wires rule out storm damage -- someone deliberately darkened the light.", source="Crime scene inspection", location="Lantern Room", importance="high", discovered=False, related_evidence=["evidence_011_cut_wires"], related_suspects=["Barnaby Slate"]),
        dict(clue_id="clue_011_alibi_broken", description="The harbor log directly contradicts Barnaby's claim of staying docked all night.", source="Evidence analysis", location="Basement", importance="critical", discovered=False, related_evidence=["evidence_011_harbor_log"], related_suspects=["Barnaby Slate"]),
        dict(clue_id="clue_011_motive", description="The unmarked manifest gives Barnaby a precise reason to want the light dark on that exact night.", source="Evidence analysis", location="Keeper's Room", importance="critical", discovered=False, related_evidence=["evidence_011_shipping_manifest"], related_suspects=["Barnaby Slate"]),
        dict(clue_id="clue_011_timeline", description="The wet boot prints place someone climbing to the lantern room at precisely the moment the light died.", source="Crime scene inspection", location="Spiral Staircase", importance="high", discovered=False, related_evidence=["evidence_011_wet_bootprints"], related_suspects=["Barnaby Slate"]),
        dict(clue_id="clue_011_aldous_fate", description="The torn logbook page suggests Aldous confronted the saboteur directly rather than simply vanishing in the storm -- his disappearance is connected, not separate.", source="Evidence analysis", location="Lantern Room", importance="medium", discovered=False, related_evidence=["evidence_011_torn_logpage"], related_suspects=[]),
    ],
    _locations=[
        dict(location_id="loc_011_entrance", name="Lighthouse Entrance", description="The heavy iron door, its usual squeak oddly silent from recent oiling.", location_type="entrance", connected_locations=["loc_011_keeper_room", "loc_011_staircase"], available_evidence=[], available_clues=[]),
        dict(location_id="loc_011_keeper_room", name="Keeper's Room", description="Aldous's quarters, neat except for a shelf pulled slightly askew.", location_type="room", connected_locations=["loc_011_entrance", "loc_011_basement"], available_evidence=["evidence_011_shipping_manifest"], available_clues=["clue_011_motive"]),
        dict(location_id="loc_011_staircase", name="Spiral Staircase", description="A narrow iron staircase winding up the tower's interior, faint wet prints on the steps.", location_type="hallway", connected_locations=["loc_011_entrance", "loc_011_lantern"], available_evidence=["evidence_011_wet_bootprints"], available_clues=["clue_011_timeline"]),
        dict(location_id="loc_011_lantern", name="Lantern Room", description="The great lamp sits dark and cold at the top of the tower, its wiring severed.", location_type="room", connected_locations=["loc_011_staircase"], available_evidence=["evidence_011_cut_wires", "evidence_011_torn_logpage"], available_clues=["clue_011_sabotage_confirmed", "clue_011_aldous_fate"]),
        dict(location_id="loc_011_basement", name="Basement", description="Storage crates and an old harbor logbook shelf, damp with sea air.", location_type="basement", connected_locations=["loc_011_keeper_room"], available_evidence=["evidence_011_harbor_log"], available_clues=["clue_011_alibi_broken"]),
    ],
))

# ---------------------------------------------------------------------------
# LEVEL 11 -- "The Manor Beneath the Fog"  (case_012)
# ---------------------------------------------------------------------------
CASES.append(dict(
    case_id="case_012",
    title="The Manor Beneath the Fog",
    description=(
        "Patriarch Edmund Thorncastle is found dead in the manor library "
        "during a fog-shrouded gala celebrating the unveiling of a newly "
        "restored family portrait. The restoration itself, it turns out, "
        "hid something no one was meant to find."
    ),
    location="Thorncastle Manor",
    crime_type="murder",
    difficulty="hard",
    correct_suspect="Adrian Vale",
    suspects=["Adrian Vale", "Butler Higgins", "Camille Thorncastle", "Investigator Reeve", "Silas the Gardener"],
    evidence=[], clues=[], status="not_started",
    _suspects=[
        dict(suspect_id="suspect_adrian_vale", name="Adrian Vale", age=47,
             occupation="Art restorer", description="Spent six months restoring the family portrait unveiled tonight -- and secretly replaced a damaged section with a forged patch Edmund had just discovered.",
             relationship_to_victim="Contracted restorer",
             alibi="Says he was in the ballroom greeting guests when Edmund was found.",
             behavior=["Left the ballroom for nearly twenty unaccounted-for minutes shortly before the body was discovered."],
             statements=[], suspicion_level=55),
        dict(suspect_id="suspect_higgins", name="Butler Higgins", age=62,
             occupation="Family butler", description="Has served the Thorncastles for four decades and discovered the body.",
             relationship_to_victim="Longtime employee",
             alibi="Says he was overseeing the kitchen staff until he went to check on Edmund.",
             behavior=["Was visibly shaken, consistent with someone who found the body rather than caused it."],
             statements=[], suspicion_level=10),
        dict(suspect_id="suspect_camille", name="Camille Thorncastle", age=29,
             occupation="Edmund's daughter", description="Set to inherit the estate, though she and Edmund had reconciled only recently after years of estrangement.",
             relationship_to_victim="Daughter",
             alibi="Says she was greeting guests in the ballroom the entire evening, corroborated by several attendees.",
             behavior=["Was the one who insisted on a full investigation rather than accepting a quiet 'natural causes' explanation."],
             statements=[], suspicion_level=15),
        dict(suspect_id="suspect_reeve", name="Investigator Reeve", age=44,
             occupation="Private investigator hired by the family", description="Hired weeks ago after Edmund grew suspicious someone close to him was hiding something.",
             relationship_to_victim="Hired investigator",
             alibi="Says he was reviewing the guest list against known art forgery rings in the servant quarters.",
             behavior=["Had compiled a private file specifically on Adrian's past restoration work before tonight."],
             statements=[], suspicion_level=20),
        dict(suspect_id="suspect_silas_gardener", name="Silas the Gardener", age=55,
             occupation="Groundskeeper", description="Maintains the manor's grounds and rarely enters the house itself.",
             relationship_to_victim="Employee",
             alibi="Says he was outside managing the fog-shrouded garden lanterns all evening.",
             behavior=["Noticed a side door left unlatched, unusual for a night with so many staff on duty."],
             statements=[], suspicion_level=10),
    ],
    _evidence=[
        dict(evidence_id="evidence_012_forged_patch", name="Forged Portrait Patch", description="A section of the restored portrait that, under close light, is clearly a modern forgery layered over the original canvas.", evidence_type="physical", location_found="Ballroom", importance="critical", discovered=False, related_suspects=["Adrian Vale"]),
        dict(evidence_id="evidence_012_confrontation_note", name="Edmund's Confrontation Note", description="A note in Edmund's own hand, found in the library, reading 'Vale -- explain the portrait tonight, or I call the appraiser myself.'", evidence_type="document", location_found="Library", importance="critical", discovered=False, related_suspects=["Adrian Vale"]),
        dict(evidence_id="evidence_012_missing_time", name="Missing Twenty Minutes", description="A guest's photograph timestamp placing Adrian absent from the ballroom during the exact window Edmund died.", evidence_type="digital", location_found="Ballroom", importance="high", discovered=False, related_suspects=["Adrian Vale"]),
        dict(evidence_id="evidence_012_solvent_smell", name="Solvent Smell", description="A faint trace of restoration solvent on the library door handle, matching Adrian's restoration kit exactly.", evidence_type="physical", location_found="Library", importance="high", discovered=False, related_suspects=["Adrian Vale"]),
        dict(evidence_id="evidence_012_investigator_file", name="Reeve's Private File", description="Investigator Reeve's file on Adrian's past forgery allegations at two other estates, compiled before tonight.", evidence_type="document", location_found="Servant Quarters", importance="medium", discovered=False, related_suspects=["Adrian Vale"]),
        dict(evidence_id="evidence_012_unlatched_door", name="Unlatched Side Door", description="A side door near the hidden corridor left unlatched, allowing a quiet route between the ballroom and library.", evidence_type="physical", location_found="Hidden Corridor", importance="low", discovered=False, related_suspects=[]),
    ],
    _clues=[
        dict(clue_id="clue_012_forgery_motive", description="The forged patch gives Adrian everything to lose the moment Edmund threatened to call in an appraiser.", source="Crime scene inspection", location="Ballroom", importance="critical", discovered=False, related_evidence=["evidence_012_forged_patch"], related_suspects=["Adrian Vale"]),
        dict(clue_id="clue_012_direct_threat", description="Edmund's own note names Adrian directly and sets tonight as the deadline -- the same night he died.", source="Evidence analysis", location="Library", importance="critical", discovered=False, related_evidence=["evidence_012_confrontation_note"], related_suspects=["Adrian Vale"]),
        dict(clue_id="clue_012_alibi_gap", description="Adrian's claimed alibi of 'greeting guests the whole time' is directly contradicted by a timestamped photograph.", source="Evidence analysis", location="Ballroom", importance="critical", discovered=False, related_evidence=["evidence_012_missing_time"], related_suspects=["Adrian Vale"]),
        dict(clue_id="clue_012_solvent_link", description="The solvent trace on the library door places Adrian's restoration kit at the scene, not just his person.", source="Crime scene inspection", location="Library", importance="high", discovered=False, related_evidence=["evidence_012_solvent_smell"], related_suspects=["Adrian Vale"]),
        dict(clue_id="clue_012_pattern", description="Reeve's file shows this isn't Adrian's first time hiding a forgery from a client -- a pattern, not a one-off.", source="Evidence analysis", location="Servant Quarters", importance="medium", discovered=False, related_evidence=["evidence_012_investigator_file"], related_suspects=["Adrian Vale"]),
        dict(clue_id="clue_012_red_herring", description="The unlatched door only shows a quiet route existed -- it doesn't by itself prove who used it, and several staff had reason to pass through.", source="Crime scene inspection", location="Hidden Corridor", importance="low", discovered=False, related_evidence=["evidence_012_unlatched_door"], related_suspects=[]),
    ],
    _locations=[
        dict(location_id="loc_012_entrance", name="Manor Entrance", description="Fog rolls through the open double doors, gala guests still murmuring in shock.", location_type="entrance", connected_locations=["loc_012_ballroom"], available_evidence=[], available_clues=[]),
        dict(location_id="loc_012_ballroom", name="Ballroom", description="The unveiled portrait still hangs above the gala, guests clustered anxiously beneath it.", location_type="room", connected_locations=["loc_012_entrance", "loc_012_library", "loc_012_servants"], available_evidence=["evidence_012_forged_patch", "evidence_012_missing_time"], available_clues=["clue_012_forgery_motive", "clue_012_alibi_gap"]),
        dict(location_id="loc_012_library", name="Library", description="Edmund's body has been removed, but his reading chair still faces the cold fireplace.", location_type="room", connected_locations=["loc_012_ballroom", "loc_012_corridor"], available_evidence=["evidence_012_confrontation_note", "evidence_012_solvent_smell"], available_clues=["clue_012_direct_threat", "clue_012_solvent_link"]),
        dict(location_id="loc_012_servants", name="Servant Quarters", description="Modest rooms below the main house, Reeve's makeshift investigation desk tucked in the corner.", location_type="room", connected_locations=["loc_012_ballroom"], available_evidence=["evidence_012_investigator_file"], available_clues=["clue_012_pattern"]),
        dict(location_id="loc_012_corridor", name="Hidden Corridor", description="A narrow servants' passage connecting the library to the manor's side entrance, rarely used by guests.", location_type="hallway", connected_locations=["loc_012_library", "loc_012_basement"], available_evidence=["evidence_012_unlatched_door"], available_clues=["clue_012_red_herring"]),
        dict(location_id="loc_012_basement", name="Basement", description="Wine cellar shelves line the walls, cool and silent beneath the gala above.", location_type="basement", connected_locations=["loc_012_corridor"], available_evidence=[], available_clues=[]),
    ],
))

# ---------------------------------------------------------------------------
# LEVEL 12 -- "The Frozen Research Facility"  (case_013)
# ---------------------------------------------------------------------------
CASES.append(dict(
    case_id="case_013",
    title="The Frozen Research Facility",
    description=(
        "Contact was lost with Arctic research outpost Kestrel Station "
        "three days ago. When a relief team arrives, lead researcher Dr. "
        "Elena Voss is found dead in the server room, her team's climate "
        "data wiped from every backup drive in the building."
    ),
    location="Kestrel Research Facility",
    crime_type="murder",
    difficulty="hard",
    correct_suspect="Preston Cole",
    suspects=["Preston Cole", "Dr. Naomi Ibrahim", "Ravi", "Dana Marsh"],
    evidence=[], clues=[], status="not_started",
    _suspects=[
        dict(suspect_id="suspect_preston_cole", name="Preston Cole", age=41,
             occupation="Corporate observer", description="Placed at the station by the facility's funding corporation, officially to 'monitor budget compliance.'",
             relationship_to_victim="Corporate liaison",
             alibi="Claims he was asleep in his quarters when the data wipe occurred.",
             behavior=["His personal laptop shows remote-access software the rest of the team never knew he had installed."],
             statements=[], suspicion_level=55),
        dict(suspect_id="suspect_naomi_ibrahim", name="Dr. Naomi Ibrahim", age=36,
             occupation="Rival climate researcher", description="Publicly disagreed with Elena's findings for over a year, though the two had recently begun collaborating again.",
             relationship_to_victim="Colleague",
             alibi="Says she was in the laboratory running an unrelated experiment overnight.",
             behavior=["Handed over her own raw data unprompted to help reconstruct what was lost."],
             statements=[], suspicion_level=15),
        dict(suspect_id="suspect_ravi", name="Ravi", age=28,
             occupation="IT technician", description="Responsible for the station's backup systems and the only one with root access to every drive.",
             relationship_to_victim="Colleague",
             alibi="Says he was troubleshooting a satellite uplink issue in the security wing.",
             behavior=["Immediately flagged the exact timestamp of the wipe without being asked to check."],
             statements=[], suspicion_level=20),
        dict(suspect_id="suspect_dana_marsh", name="Dana Marsh", age=45,
             occupation="Security chief", description="Oversees the facility's access logs and physical security.",
             relationship_to_victim="Colleague",
             alibi="Says she was on her scheduled perimeter check when Elena died.",
             behavior=["Provided access logs proactively, including logs that implicated a colleague."],
             statements=[], suspicion_level=10),
    ],
    _evidence=[
        dict(evidence_id="evidence_013_remote_access", name="Hidden Remote-Access Software", description="Software on Preston's laptop capable of wiping remote drives, installed weeks before Elena's death and hidden from the team.", evidence_type="digital", location_found="Server Room", importance="critical", discovered=False, related_suspects=["Preston Cole"]),
        dict(evidence_id="evidence_013_corporate_memo", name="Corporate Memo", description="An internal memo instructing Preston to 'ensure the Kestrel dataset does not reach publication' before quarterly results are finalized.", evidence_type="document", location_found="Facility Entrance", importance="critical", discovered=False, related_suspects=["Preston Cole"]),
        dict(evidence_id="evidence_013_access_log", name="Server Room Access Log", description="A badge-swipe log placing Preston in the server room at the exact time of Elena's death, despite his claimed alibi.", evidence_type="document", location_found="Security Wing", importance="high", discovered=False, related_suspects=["Preston Cole"]),
        dict(evidence_id="evidence_013_broken_glove", name="Torn Insulated Glove", description="A torn cold-weather glove fiber caught in the server rack door, matching Preston's issued gear, not Elena's or Ravi's.", evidence_type="physical", location_found="Server Room", importance="high", discovered=False, related_suspects=["Preston Cole"]),
        dict(evidence_id="evidence_013_ibrahim_data", name="Ibrahim's Raw Data Backup", description="Naomi's independently stored raw data, offered freely and untouched by the wipe.", evidence_type="digital", location_found="Laboratory", importance="low", discovered=False, related_suspects=["Dr. Naomi Ibrahim"]),
    ],
    _clues=[
        dict(clue_id="clue_013_software_intent", description="The remote-wipe software was installed weeks in advance, ruling out a spur-of-the-moment act.", source="Evidence analysis", location="Server Room", importance="critical", discovered=False, related_evidence=["evidence_013_remote_access"], related_suspects=["Preston Cole"]),
        dict(clue_id="clue_013_motive", description="The corporate memo gives Preston direct, documented orders to suppress the exact dataset that was wiped.", source="Evidence analysis", location="Facility Entrance", importance="critical", discovered=False, related_evidence=["evidence_013_corporate_memo"], related_suspects=["Preston Cole"]),
        dict(clue_id="clue_013_alibi_broken", description="The badge log directly contradicts Preston's claim of being asleep -- he was in the server room at the critical moment.", source="Crime scene inspection", location="Security Wing", importance="critical", discovered=False, related_evidence=["evidence_013_access_log"], related_suspects=["Preston Cole"]),
        dict(clue_id="clue_013_glove_match", description="The torn glove fiber physically places Preston at the server rack itself, not just in the room.", source="Crime scene inspection", location="Server Room", importance="high", discovered=False, related_evidence=["evidence_013_broken_glove"], related_suspects=["Preston Cole"]),
        dict(clue_id="clue_013_red_herring", description="Naomi's rivalry with Elena was professional, not personal -- her freely offered backup data clears her of any involvement.", source="Evidence analysis", location="Laboratory", importance="low", discovered=False, related_evidence=["evidence_013_ibrahim_data"], related_suspects=["Dr. Naomi Ibrahim"]),
    ],
    _locations=[
        dict(location_id="loc_013_entrance", name="Facility Entrance", description="Wind howls against reinforced doors; a corporate courier bag lies unopened on the entry bench.", location_type="entrance", connected_locations=["loc_013_lab", "loc_013_security"], available_evidence=["evidence_013_corporate_memo"], available_clues=["clue_013_motive"]),
        dict(location_id="loc_013_lab", name="Laboratory", description="Rows of climate samples still humming in refrigerated cases.", location_type="room", connected_locations=["loc_013_entrance", "loc_013_observation"], available_evidence=["evidence_013_ibrahim_data"], available_clues=["clue_013_red_herring"]),
        dict(location_id="loc_013_observation", name="Observation Room", description="Monitors that once streamed live data now show only error screens.", location_type="room", connected_locations=["loc_013_lab", "loc_013_server"], available_evidence=[], available_clues=[]),
        dict(location_id="loc_013_server", name="Server Room", description="Racks of drives, one rack door left ajar with a torn glove fiber caught in the hinge.", location_type="room", connected_locations=["loc_013_observation", "loc_013_underground"], available_evidence=["evidence_013_remote_access", "evidence_013_broken_glove"], available_clues=["clue_013_software_intent", "clue_013_glove_match"]),
        dict(location_id="loc_013_security", name="Security Wing", description="A bank of badge-swipe terminals logging every door in the facility.", location_type="room", connected_locations=["loc_013_entrance"], available_evidence=["evidence_013_access_log"], available_clues=["clue_013_alibi_broken"]),
        dict(location_id="loc_013_underground", name="Underground Section", description="Sub-basement cabling tunnels running beneath the entire facility.", location_type="basement", connected_locations=["loc_013_server"], available_evidence=[], available_clues=[]),
    ],
))

# ---------------------------------------------------------------------------
# LEVEL 13 -- "The Town Beneath the Lake"  (case_014)
# ---------------------------------------------------------------------------
CASES.append(dict(
    case_id="case_014",
    title="The Town Beneath the Lake",
    description=(
        "A decades-long drought has drained Lake Ashwell, revealing the "
        "submerged town of Merrow that was flooded to build the reservoir "
        "in 1962. Inside the reemerged town hall, a lockbox believed lost "
        "in the flood is gone -- and it vanished only in the last few "
        "days, long after the lake receded."
    ),
    location="The Sunken Town of Merrow",
    crime_type="theft",
    difficulty="hard",
    correct_suspect="Desmond Pike",
    suspects=["Desmond Pike", "Ilsa Bram", "Wyatt Merrow", "Fran Doyle"],
    evidence=[], clues=[], status="not_started",
    _suspects=[
        dict(suspect_id="suspect_desmond_pike", name="Desmond Pike", age=37,
             occupation="Treasure hunter", description="Has been documenting drought-exposed lakebeds online for years, hoping to find exactly this kind of lockbox.",
             relationship_to_victim="Stranger",
             alibi="Claims he only just arrived in town today, cameras rolling for his channel.",
             behavior=["His own uploaded footage from three days ago already shows him standing at the town hall steps."],
             statements=[], suspicion_level=55),
        dict(suspect_id="suspect_ilsa_bram", name="Ilsa Bram", age=52,
             occupation="Local historian", description="Has researched Merrow's flooding for a planned book and knows every building's layout by heart.",
             relationship_to_victim="Researcher",
             alibi="Says she was cataloguing the old hotel's foundation the whole week.",
             behavior=["Was the one who alerted authorities the moment she noticed the lockbox missing."],
             statements=[], suspicion_level=10),
        dict(suspect_id="suspect_wyatt_merrow", name="Wyatt Merrow", age=44,
             occupation="Descendant of the town's founder", description="His family lost everything when Merrow was flooded and has long claimed the lockbox held family gold.",
             relationship_to_victim="Family connection",
             alibi="Says he only came to see his ancestral town for the first time since childhood.",
             behavior=["Seemed more interested in photographing the ruins than searching for the lockbox."],
             statements=[], suspicion_level=15),
        dict(suspect_id="suspect_fran_doyle", name="Fran Doyle", age=48,
             occupation="Insurance adjuster", description="Sent to assess the reservoir authority's liability now that the town has resurfaced.",
             relationship_to_victim="Professional visitor",
             alibi="Says she spent the week only at the flooded street's edge, taking structural photos.",
             behavior=["Filed her report before the lockbox was even reported missing, oddly premature."],
             statements=[], suspicion_level=20),
    ],
    _evidence=[
        dict(evidence_id="evidence_014_upload_timestamp", name="Timestamped Video Upload", description="Desmond's own public video, timestamped three days before the theft was noticed, showing him at the town hall steps.", evidence_type="digital", location_found="Town Hall", importance="critical", discovered=False, related_suspects=["Desmond Pike"]),
        dict(evidence_id="evidence_014_lockbox_dent", name="Fresh Lockbox-Shaped Impression", description="A rectangular impression in the mud, edges sharp and recent -- not decades-old silt settling.", evidence_type="physical", location_found="Town Hall", importance="high", discovered=False, related_suspects=["Desmond Pike"]),
        dict(evidence_id="evidence_014_channel_post", name="Public Channel Post", description="A post on Desmond's channel from months ago naming this exact lockbox as his 'holy grail' find.", evidence_type="digital", location_found="Flooded Street", importance="critical", discovered=False, related_suspects=["Desmond Pike"]),
        dict(evidence_id="evidence_014_scare_props", name="Staged 'Haunting' Props", description="Fishing line and a small speaker rigged near the old hotel, designed to make the ruins seem haunted and scare off other visitors.", evidence_type="physical", location_found="Old Hotel", importance="medium", discovered=False, related_suspects=["Desmond Pike"]),
        dict(evidence_id="evidence_014_tunnel_mud", name="Fresh Mud Trail", description="A trail of fresh mud through the underground tunnel, leading away from the town hall toward the exposed shoreline.", evidence_type="physical", location_found="Underground Tunnel", importance="low", discovered=False, related_suspects=["Desmond Pike"]),
    ],
    _clues=[
        dict(clue_id="clue_014_presence_proof", description="Desmond's own footage places him at the scene days before he claims to have arrived.", source="Evidence analysis", location="Town Hall", importance="critical", discovered=False, related_evidence=["evidence_014_upload_timestamp"], related_suspects=["Desmond Pike"]),
        dict(clue_id="clue_014_recency", description="The impression in the mud is far too crisp to have survived decades underwater -- it was made recently, after the theft.", source="Crime scene inspection", location="Town Hall", importance="high", discovered=False, related_evidence=["evidence_014_lockbox_dent"], related_suspects=["Desmond Pike"]),
        dict(clue_id="clue_014_motive", description="Desmond publicly named this exact lockbox as his life's goal long before the drought even exposed the town.", source="Evidence analysis", location="Flooded Street", importance="critical", discovered=False, related_evidence=["evidence_014_channel_post"], related_suspects=["Desmond Pike"]),
        dict(clue_id="clue_014_staged_scare", description="The rigged 'haunting' props show a deliberate effort to keep others away from the ruins while he searched.", source="Crime scene inspection", location="Old Hotel", importance="high", discovered=False, related_evidence=["evidence_014_scare_props"], related_suspects=["Desmond Pike"]),
        dict(clue_id="clue_014_escape_route", description="The fresh mud trail traces Desmond's likely path out of town with the lockbox in hand.", source="Crime scene inspection", location="Underground Tunnel", importance="medium", discovered=False, related_evidence=["evidence_014_tunnel_mud"], related_suspects=["Desmond Pike"]),
    ],
    _locations=[
        dict(location_id="loc_014_street", name="Flooded Street", description="Cracked pavement still slick with decades of lakebed silt, storefronts frozen in 1962.", location_type="outdoor", connected_locations=["loc_014_hotel", "loc_014_hall"], available_evidence=["evidence_014_channel_post"], available_clues=["clue_014_motive"]),
        dict(location_id="loc_014_hotel", name="Old Hotel", description="A collapsed sign still reads 'Merrow Arms,' fishing line rigged suspiciously near the doorway.", location_type="room", connected_locations=["loc_014_street"], available_evidence=["evidence_014_scare_props"], available_clues=["clue_014_staged_scare"]),
        dict(location_id="loc_014_hall", name="Town Hall", description="The vault room stands open, a rectangular gap in the silt where the lockbox once sat.", location_type="room", connected_locations=["loc_014_street", "loc_014_house"], available_evidence=["evidence_014_upload_timestamp", "evidence_014_lockbox_dent"], available_clues=["clue_014_presence_proof", "clue_014_recency"]),
        dict(location_id="loc_014_house", name="Abandoned House", description="A modest home, family initials still carved above the doorframe.", location_type="room", connected_locations=["loc_014_hall", "loc_014_tunnel"], available_evidence=[], available_clues=[]),
        dict(location_id="loc_014_tunnel", name="Underground Tunnel", description="An old drainage tunnel, exposed for the first time in sixty years, mud still soft underfoot.", location_type="tunnel", connected_locations=["loc_014_house"], available_evidence=["evidence_014_tunnel_mud"], available_clues=["clue_014_escape_route"]),
    ],
))

# ---------------------------------------------------------------------------
# LEVEL 14 -- "The Blackwood Underground"  (case_015)
# ---------------------------------------------------------------------------
CASES.append(dict(
    case_id="case_015",
    title="The Blackwood Underground",
    description=(
        "Renovation work beneath Blackwood Mansion -- site of the very "
        "first case -- breaks through into a sealed underground complex "
        "no one knew existed. Inside, an archive documents years of "
        "quiet operations run from beneath the estate, and the file on "
        "the Hartley necklace theft is open on a desk, annotated in a "
        "hand no one at the mansion recognizes."
    ),
    location="Beneath Blackwood Mansion",
    crime_type="conspiracy",
    difficulty="hard",
    correct_suspect="Julian Hartley",
    suspects=["Butler James", "Julian Hartley", "Petra Voss", "Dax Reilly"],
    evidence=[], clues=[], status="not_started",
    _suspects=[
        dict(suspect_id="suspect_butler_james_returns", name="Butler James", age=54,
             occupation="Butler", description="The same butler from the original necklace case, now retired but summoned back after the discovery.",
             relationship_to_victim="Former employee",
             alibi="Says he never knew this underground complex existed in all his years of service.",
             behavior=["Recognized one specific archive ledger instantly, though he denied ever seeing this level of the house."],
             statements=[], suspicion_level=20),
        dict(suspect_id="suspect_julian_hartley", name="Julian Hartley", age=58,
             occupation="Mrs. Hartley's estranged brother", description="Vanished from the family's life decades ago after a falling-out, and has secretly financed operations from beneath the estate ever since.",
             relationship_to_victim="Family",
             alibi="Claims he hasn't set foot on the property in over twenty years.",
             behavior=["Knew the complex's layout from memory, correcting the survey team's map before they'd finished drawing it."],
             statements=[], suspicion_level=55),
        dict(suspect_id="suspect_petra_voss", name="Petra Voss", age=41,
             occupation="Archivist", description="Hired by the current Hartley estate to catalogue whatever the renovation crew found.",
             relationship_to_victim="Contracted researcher",
             alibi="Says she only arrived after the complex was already discovered.",
             behavior=["Flagged the necklace file's annotations as suspicious the moment she saw them."],
             statements=[], suspicion_level=10),
        dict(suspect_id="suspect_dax_reilly", name="Dax Reilly", age=36,
             occupation="Security contractor", description="Hired to secure the newly discovered complex against looters.",
             relationship_to_victim="Contractor",
             alibi="Says he was posted at the entrance the entire time.",
             behavior=["Was unusually familiar with the complex's original security system for someone hired just this week."],
             statements=[], suspicion_level=25),
    ],
    _evidence=[
        dict(evidence_id="evidence_015_annotated_file", name="Annotated Necklace File", description="The original Hartley necklace case file, annotated in handwriting that matches samples later confirmed to be Julian's.", evidence_type="document", location_found="Investigation Room", importance="critical", discovered=False, related_suspects=["Julian Hartley"]),
        dict(evidence_id="evidence_015_ledger", name="Decades-Long Ledger", description="A ledger tracking years of quiet payments and operations, all traced to accounts under Julian's control.", evidence_type="document", location_found="Archive", importance="critical", discovered=False, related_suspects=["Julian Hartley"]),
        dict(evidence_id="evidence_015_handwriting_sample", name="Handwriting Sample", description="A personal letter from Julian confirmed by a handwriting expert to match the necklace file's annotations exactly.", evidence_type="document", location_found="Hidden Laboratory", importance="high", discovered=False, related_suspects=["Julian Hartley"]),
        dict(evidence_id="evidence_015_key_fob", name="Modern Key Fob", description="A modern electronic key fob programmed to the complex's original lock system, found in a drawer only Julian could have accessed.", evidence_type="physical", location_found="Restricted Area", importance="high", discovered=False, related_suspects=["Julian Hartley"]),
        dict(evidence_id="evidence_015_james_denial", name="James's Sworn Statement", description="A statement from Butler James, sworn and consistent, that he never knew of the complex despite decades of service upstairs.", evidence_type="document", location_found="Underground Entrance", importance="low", discovered=False, related_suspects=["Butler James"]),
    ],
    _clues=[
        dict(clue_id="clue_015_handwriting_match", description="A handwriting expert confirms the file's annotations were written by Julian, not anyone currently employed at the estate.", source="Evidence analysis", location="Investigation Room", importance="critical", discovered=False, related_evidence=["evidence_015_annotated_file", "evidence_015_handwriting_sample"], related_suspects=["Julian Hartley"]),
        dict(clue_id="clue_015_financial_trail", description="Every account in the ledger traces back through shell companies to Julian's control.", source="Evidence analysis", location="Archive", importance="critical", discovered=False, related_evidence=["evidence_015_ledger"], related_suspects=["Julian Hartley"]),
        dict(clue_id="clue_015_key_access", description="Only someone with the original master key fob -- reprogrammed by Julian himself -- could have accessed the restricted area undetected.", source="Crime scene inspection", location="Restricted Area", importance="high", discovered=False, related_evidence=["evidence_015_key_fob"], related_suspects=["Julian Hartley"]),
        dict(clue_id="clue_015_contradiction", description="Julian claimed he hadn't set foot on the property in twenty years, yet he corrected the survey map from memory before it was finished.", source="Suspect questioning", location="Deep Corridor", importance="critical", discovered=False, related_evidence=["evidence_015_ledger"], related_suspects=["Julian Hartley"]),
        dict(clue_id="clue_015_james_cleared", description="James's account is consistent under scrutiny and matches the physical evidence -- he genuinely never knew the complex existed.", source="Suspect questioning", location="Underground Entrance", importance="low", discovered=False, related_evidence=["evidence_015_james_denial"], related_suspects=["Butler James"]),
    ],
    _locations=[
        dict(location_id="loc_015_entrance", name="Underground Entrance", description="A rough-cut breach in the mansion's original foundation, dust still settling from the renovation crew's drill.", location_type="entrance", connected_locations=["loc_015_archive", "loc_015_investigation"], available_evidence=["evidence_015_james_denial"], available_clues=["clue_015_james_cleared"]),
        dict(location_id="loc_015_archive", name="Archive", description="Shelves of ledgers and files, organized with a precision no casual visitor could manage.", location_type="room", connected_locations=["loc_015_entrance", "loc_015_lab"], available_evidence=["evidence_015_ledger"], available_clues=["clue_015_financial_trail"]),
        dict(location_id="loc_015_lab", name="Hidden Laboratory", description="An old workspace repurposed for document forgery and analysis, tools still laid out on the bench.", location_type="room", connected_locations=["loc_015_archive"], available_evidence=["evidence_015_handwriting_sample"], available_clues=["clue_015_handwriting_match"]),
        dict(location_id="loc_015_investigation", name="Investigation Room", description="A wall of case files, the necklace file left open at the center as though someone wanted it found.", location_type="room", connected_locations=["loc_015_entrance", "loc_015_restricted"], available_evidence=["evidence_015_annotated_file"], available_clues=[]),
        dict(location_id="loc_015_restricted", name="Restricted Area", description="A reinforced door with a modern electronic lock, out of place among the complex's older fixtures.", location_type="room", connected_locations=["loc_015_investigation", "loc_015_corridor"], available_evidence=["evidence_015_key_fob"], available_clues=["clue_015_key_access"]),
        dict(location_id="loc_015_corridor", name="Deep Corridor", description="The complex's furthest reach, a hand-drawn map pinned to the wall with recent corrections in fresh ink.", location_type="hallway", connected_locations=["loc_015_restricted"], available_evidence=[], available_clues=["clue_015_contradiction"]),
    ],
))

# ---------------------------------------------------------------------------
# LEVEL 15 -- "THE FINAL CASE"  (case_016)
# ---------------------------------------------------------------------------
CASES.append(dict(
    case_id="case_016",
    title="THE FINAL CASE",
    description=(
        "Every case so far has led here. The ledger from beneath Blackwood "
        "Mansion names a single figure behind years of quiet manipulation: "
        "a collector and self-styled 'curator of mysteries' known only as "
        "the Architect, operating out of a private chamber built to look "
        "like an archive of every case the detective has ever solved -- "
        "because it is one."
    ),
    location="The Architect's Chamber",
    crime_type="conspiracy",
    difficulty="hard",
    correct_suspect="Dr. Elias Wilmarth",
    suspects=["Dr. Elias Wilmarth", "Julian Hartley", "Renee Ashworth", "Corinne Vasquez", "Petra Voss"],
    evidence=[], clues=[], status="not_started",
    _suspects=[
        dict(suspect_id="suspect_elias_wilmarth", name="Dr. Elias Wilmarth", age=63,
             occupation="Private collector and self-described 'curator of mysteries'", description="Has spent decades quietly funding, observing, and in some cases orchestrating the very cases the detective has solved -- treating them as a private collection to study.",
             relationship_to_victim="Mastermind",
             alibi="Claims to be merely an admirer who 'collects the aftermath, never causes it.'",
             behavior=["His personal ledger cross-references every prior case by name, including details never made public."],
             statements=[], suspicion_level=60),
        dict(suspect_id="suspect_julian_hartley_final", name="Julian Hartley", age=58,
             occupation="Financier", description="Revealed beneath Blackwood Mansion to have long financed operations on Wilmarth's behalf.",
             relationship_to_victim="Associate",
             alibi="Says he only followed instructions and never met Wilmarth in person.",
             behavior=["Cooperated fully once shown the financial trail, confirming Wilmarth issued every order."],
             statements=[], suspicion_level=20),
        dict(suspect_id="suspect_renee_ashworth_final", name="Renee Ashworth", age=31,
             occupation="Former hotel heir", description="Recruited early on by Wilmarth's network after her deed scheme, now cooperating with the investigation.",
             relationship_to_victim="Recruited associate",
             alibi="Says she was promised protection from prosecution in exchange for information.",
             behavior=["Provided a detailed account of how Wilmarth's agents first approached her."],
             statements=[], suspicion_level=10),
        dict(suspect_id="suspect_corinne_vasquez_final", name="Corinne Vasquez", age=45,
             occupation="Art collector's agent", description="Her mural acquisition at Millbrook Station was, it turns out, commissioned by Wilmarth under a shell client's name.",
             relationship_to_victim="Recruited associate",
             alibi="Says she never knew her true client's identity until now.",
             behavior=["Recognized Wilmarth's handwriting on a commission letter instantly."],
             statements=[], suspicion_level=15),
        dict(suspect_id="suspect_petra_voss_final", name="Petra Voss", age=41,
             occupation="Archivist", description="Hired to catalogue the Blackwood complex, she followed the paper trail here herself.",
             relationship_to_victim="Independent investigator",
             alibi="Says she came only to confirm what the ledger implied.",
             behavior=["Was the one who first connected Wilmarth's name across every prior case file."],
             statements=[], suspicion_level=5),
    ],
    _evidence=[
        dict(evidence_id="evidence_016_master_ledger", name="The Architect's Master Ledger", description="A single ledger cross-referencing every prior case -- the necklace, the hotel deed, the mural, the lighthouse sabotage -- all funded or directed from this chamber.", evidence_type="document", location_found="The Archive of Cases", importance="critical", discovered=False, related_suspects=["Dr. Elias Wilmarth"]),
        dict(evidence_id="evidence_016_commission_letters", name="Signed Commission Letters", description="Commission letters in Wilmarth's own hand, instructing agents across a decade of cases -- including Corinne Vasquez at Millbrook Station.", evidence_type="document", location_found="The Society's Chamber", importance="critical", discovered=False, related_suspects=["Dr. Elias Wilmarth"]),
        dict(evidence_id="evidence_016_case_trophies", name="Case Trophy Collection", description="A locked cabinet holding physical mementos from prior cases -- including an item matching the Millbrook mural fragment.", evidence_type="physical", location_found="The Archive of Cases", importance="high", discovered=False, related_suspects=["Dr. Elias Wilmarth"]),
        dict(evidence_id="evidence_016_confession_recording", name="Recorded Confession Fragment", description="An old recording of Wilmarth explaining his 'collection' philosophy to an unnamed associate, recovered from a hidden recorder.", evidence_type="digital", location_found="The Final Confrontation Room", importance="critical", discovered=False, related_suspects=["Dr. Elias Wilmarth"]),
        dict(evidence_id="evidence_016_financial_web", name="Financial Web Diagram", description="A hand-drawn diagram connecting Julian Hartley's accounts, Renee Ashworth's recruitment, and Corinne Vasquez's commissions -- all converging on Wilmarth.", evidence_type="document", location_found="Detective's Office", importance="high", discovered=False, related_suspects=["Dr. Elias Wilmarth"]),
    ],
    _clues=[
        dict(clue_id="clue_016_pattern_confirmed", description="The master ledger proves every prior case in the campaign traces back to the same funding source and the same handwriting.", source="Evidence analysis", location="The Archive of Cases", importance="critical", discovered=False, related_evidence=["evidence_016_master_ledger"], related_suspects=["Dr. Elias Wilmarth"]),
        dict(clue_id="clue_016_direct_orders", description="The commission letters are signed and dated, directly linking Wilmarth to specific instructions given to specific agents.", source="Evidence analysis", location="The Society's Chamber", importance="critical", discovered=False, related_evidence=["evidence_016_commission_letters"], related_suspects=["Dr. Elias Wilmarth"]),
        dict(clue_id="clue_016_trophy_match", description="The mural fragment in the trophy cabinet is the exact piece cut from Millbrook Station -- physical proof, not just paperwork.", source="Crime scene inspection", location="The Archive of Cases", importance="high", discovered=False, related_evidence=["evidence_016_case_trophies"], related_suspects=["Dr. Elias Wilmarth"]),
        dict(clue_id="clue_016_own_words", description="Wilmarth's recorded voice describes orchestrating cases 'to study how ordinary people behave when their world tilts' -- a confession in his own words.", source="Evidence analysis", location="The Final Confrontation Room", importance="critical", discovered=False, related_evidence=["evidence_016_confession_recording"], related_suspects=["Dr. Elias Wilmarth"]),
        dict(clue_id="clue_016_web_convergence", description="Every financial thread from every prior suspect converges on one name at the center of the diagram: Wilmarth.", source="Evidence analysis", location="Detective's Office", importance="high", discovered=False, related_evidence=["evidence_016_financial_web"], related_suspects=["Dr. Elias Wilmarth"]),
    ],
    _locations=[
        dict(location_id="loc_016_office", name="Detective's Office", description="Case files from the entire campaign pinned across every wall, red thread connecting them all to one point.", location_type="room", connected_locations=["loc_016_ruins", "loc_016_archive"], available_evidence=["evidence_016_financial_web"], available_clues=["clue_016_web_convergence"]),
        dict(location_id="loc_016_ruins", name="Blackwood Mansion Ruins", description="The mansion where it all began, now partially excavated down to the complex beneath it.", location_type="room", connected_locations=["loc_016_office", "loc_016_chamber"], available_evidence=[], available_clues=[]),
        dict(location_id="loc_016_chamber", name="The Society's Chamber", description="A private meeting room, its long table still set as though a council once gathered here.", location_type="room", connected_locations=["loc_016_ruins", "loc_016_archive"], available_evidence=["evidence_016_commission_letters"], available_clues=["clue_016_direct_orders"]),
        dict(location_id="loc_016_archive", name="The Archive of Cases", description="A private museum of every mystery solved so far, each one catalogued like a trophy.", location_type="room", connected_locations=["loc_016_office", "loc_016_chamber", "loc_016_confrontation"], available_evidence=["evidence_016_master_ledger", "evidence_016_case_trophies"], available_clues=["clue_016_pattern_confirmed", "clue_016_trophy_match"]),
        dict(location_id="loc_016_confrontation", name="The Final Confrontation Room", description="A single chair faces a wall of one-way glass -- the Architect's last vantage point.", location_type="room", connected_locations=["loc_016_archive"], available_evidence=["evidence_016_confession_recording"], available_clues=["clue_016_own_words"]),
    ],
))

print(f"Prepared {len(CASES)} case definitions so far (part 1).")

if __name__ == "__main__":
    for case in CASES:
        suspects = case.pop("_suspects")
        evidence = case.pop("_evidence")
        clues = case.pop("_clues")
        locations = case.pop("_locations")
        cid = case["case_id"]
        write(CASES_DIR / f"{cid}.json", case)
        write(CASES_DIR / "suspects" / f"{cid}_suspects.json", suspects)
        write(CASES_DIR / "evidence" / f"{cid}_evidence.json", evidence)
        write(CASES_DIR / "clues" / f"{cid}_clues.json", clues)
        write(CASES_DIR / "locations" / f"{cid}_locations.json", locations)
    print(f"Wrote {len(CASES)} cases.")
