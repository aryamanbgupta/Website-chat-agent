"""Rule-based intent classifier — runs BEFORE the LLM, zero latency/cost."""

import re
from enum import Enum


class Intent(Enum):
    ON_TOPIC = "on_topic"
    GREETING = "greeting"
    OTHER_APPLIANCE = "other_appliance"
    OFF_TOPIC = "off_topic"


# Patterns
APPLIANCE_KEYWORDS = re.compile(
    r"\b(fridge|refrigerator|freezer|ice\s*maker|dishwasher|"
    r"dish\s*washer|cooler|defrost)\b",
    re.IGNORECASE,
)

PART_PATTERNS = re.compile(
    r"(PS\d{5,10}|part\s*(number|#|no)|replacement|gasket|valve|"
    r"filter|pump|motor|hose|seal|thermostat|compressor|fan|"
    r"door\s*(shelf|bin|rack|handle|seal)|ice\s*maker|drain|"
    r"water\s*inlet|dispenser|evaporator|condenser|relay|switch|"
    r"bracket|shelf|drawer|spray\s*arm|rack|roller)",
    re.IGNORECASE,
)

REPAIR_KEYWORDS = re.compile(
    r"\b(fix|repair|replace|install|broken|not\s*working|"
    r"won'?t|doesn'?t|leaking|noisy|noise|error|code|"
    r"reset|troubleshoot|diagnose|symptom|problem|issue)\b",
    re.IGNORECASE,
)

OTHER_APPLIANCE_KEYWORDS = re.compile(
    r"\b(washer|washing\s*machine|dryer|clothes\s*dryer|"
    r"oven|stove|range|cooktop|microwave|"
    r"air\s*conditioner|ac\s*unit|furnace|"
    r"garbage\s*disposal|trash\s*compactor|"
    r"dehumidifier|humidifier|water\s*heater)\b",
    re.IGNORECASE,
)

GREETING_PATTERNS = re.compile(
    r"^\s*(hi|hello|hey|howdy|good\s*(morning|afternoon|evening)|"
    r"thanks|thank\s*you|bye|goodbye|see\s*you|help)\s*[!.?]?\s*$",
    re.IGNORECASE,
)

MODEL_NUMBER_PATTERN = re.compile(r"\b[A-Z]{2,5}\d{3,}[A-Z\d]*\b", re.IGNORECASE)

# Off-topic redirect message
OFF_TOPIC_MESSAGE = (
    "I'm a PartSelect assistant specializing in **refrigerator and dishwasher** "
    "parts and repairs. I can help you find parts, diagnose problems, check "
    "compatibility, and provide installation guidance.\n\n"
    "How can I help with your refrigerator or dishwasher today?"
)

OTHER_APPLIANCE_MESSAGE = (
    "I specialize in **refrigerator and dishwasher** parts. "
    "For other appliance parts, please visit [PartSelect.com](https://www.partselect.com).\n\n"
    "Is there anything I can help with for your refrigerator or dishwasher?"
)


def classify(message: str) -> Intent:
    """Classify user message intent. Zero latency, zero cost."""
    text = message.strip()

    # Greeting check (must be short standalone message)
    if GREETING_PATTERNS.match(text):
        return Intent.GREETING

    # On-topic signals
    has_appliance = bool(APPLIANCE_KEYWORDS.search(text))
    has_part = bool(PART_PATTERNS.search(text))
    has_repair = bool(REPAIR_KEYWORDS.search(text))
    has_model = bool(MODEL_NUMBER_PATTERN.search(text))
    has_ps = bool(re.search(r"PS\d{5,10}", text, re.IGNORECASE))

    # Other appliance check — must come BEFORE repair keyword check
    # so "fix my washing machine" → other_appliance, not on_topic
    has_other_appliance = bool(OTHER_APPLIANCE_KEYWORDS.search(text))
    if has_other_appliance and not has_appliance and not has_part and not has_ps:
        return Intent.OTHER_APPLIANCE

    if has_appliance or has_part or has_ps or has_model:
        return Intent.ON_TOPIC

    if has_repair:
        return Intent.ON_TOPIC

    # Short follow-up messages in a conversation context should be on-topic
    # (e.g. "yes", "that one", "how much?")
    if len(text.split()) <= 4:
        return Intent.ON_TOPIC

    return Intent.OFF_TOPIC
