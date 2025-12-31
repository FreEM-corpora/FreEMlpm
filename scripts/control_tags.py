# ============================================================
# Imports
# ============================================================

from collections import Counter, defaultdict
import re

# ============================================================
# User configuration
# ============================================================

FICHIER_TSV = "Data/presto_max_v5.5.txt"
NB_EXPECTED_COLUMNS = 8

# Valid entities for columns 4 and 5
VALID_ENTITIES_COL4 = {
    "amount", "event", "func", "loc",
    "org", "pers", "prod", "time"
}


# ============================================================
# Regex definitions
# ============================================================

# Column 4: exact entity, no suffix, or O
REGEX_COL4_VALID = re.compile(
    rf"^(O|[BI]-({'|'.join(VALID_ENTITIES_COL4)}))$"
)

# Column 5: entity with optional suffix, or O
REGEX_COL5_VALID = re.compile(
    rf"^(O|[BI]-({'|'.join(VALID_ENTITIES_COL4)})(\.\w+)*)$"
)

# Column 6: named entity continuation, allow 'O'
VALID_SUFFIXES_COL6 = {"kind", "name", "qualifier", "range-mark", "title", "unit", "val"}
REGEX_COL6_VALID = re.compile(
    rf"^(O|[BI]-comp(\.({'|'.join(VALID_SUFFIXES_COL6)}))*)$"
)

# Column 7: composition/boundary tags, optional suffixes
REGEX_COL7_VALID = re.compile(
    rf"^(O|[BI]-({'|'.join(VALID_ENTITIES_COL4)})(\.\w+)*)$"
)

# Entity extractor for col4/col5 consistency
REGEX_ENTITY_EXTRACT = re.compile(r"^[BI]-(\w+)")


# ============================================================
# Core analysis functions
# ============================================================

def analyse_tsv(filepath):
    """
    Analyze TSV file for:
    - column count validation
    - tag frequency
    - invalid tags (regex validation)
    - column 4 / 5 entity consistency
    - B-I sequence consistency for columns 4, 5, 6
    """

    # Statistics and error tracking
    tag_counts = defaultdict(Counter)
    tag_occurrences = defaultdict(lambda: defaultdict(list))
    column_errors = []
    col4_col5_inconsistencies = []
    bi_sequence_errors = []

    # Track previous line's tags for B-I sequence validation
    # Keys: column index (4, 5, 6), Values: previous tag
    prev_tags = {4: "O", 5: "O", 6: "O"}
    prev_line_number = 0

    with open(filepath, encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.rstrip("\n")

            # Empty lines reset B-I sequence tracking
            if not line:
                prev_tags = {4: "O", 5: "O", 6: "O"}
                continue

            # Split on one or more tabs
            columns = re.split(r'\t+', line)

            # === VALIDATION 1: Column count ===
            if len(columns) != NB_EXPECTED_COLUMNS:
                column_errors.append((line_number, len(columns), line))
                # Reset B-I tracking on malformed lines
                prev_tags = {4: "O", 5: "O", 6: "O"}
                continue

            # Skip header line
            if columns[0] == "form":
                continue

            # === VALIDATION 2: Tag frequency and collection ===
            # Count tags in columns 4–7 and store their occurrences
            for col_index, value in enumerate(columns[3:-1], start=4):
                value = value.strip()
                tag_counts[col_index][value] += 1
                tag_occurrences[col_index][value].append((line_number, line))

            # === VALIDATION 3: Column 4 / 5 entity consistency ===
            # Both columns should have the same base entity (e.g., func in B-func and B-func.ind)
            col4, col5 = columns[3], columns[4]
            m4 = REGEX_ENTITY_EXTRACT.match(col4)
            m5 = REGEX_ENTITY_EXTRACT.match(col5)
            if m4 and m5 and m4.group(1) != m5.group(1):
                col4_col5_inconsistencies.append(
                    (line_number, col4, col5, line)
                )

            # === VALIDATION 4: B-I sequence consistency ===
            # For columns 4, 5, 6: if a tag starts with I-, the previous line
            # must have either B- or I- with the same entity and suffix
            for col_index in [4, 5, 6]:
                current_tag = columns[col_index - 1].strip()
                
                # Check if current tag is an I- tag
                if current_tag.startswith("I-"):
                    # Expected tags: either B- or I- with same entity/suffix
                    entity_suffix = current_tag[2:]  # Extract part after I-
                    expected_b_tag = "B-" + entity_suffix
                    expected_i_tag = "I-" + entity_suffix
                    
                    # Verify that previous tag matches one of the expected tags
                    if prev_tags[col_index] not in (expected_b_tag, expected_i_tag):
                        bi_sequence_errors.append((
                            line_number,
                            col_index,
                            current_tag,
                            prev_tags[col_index],
                            prev_line_number,
                            line
                        ))
                
                # Update tracking: store current tag as "previous" for next iteration
                prev_tags[col_index] = current_tag
            
            prev_line_number = line_number

    return tag_counts, tag_occurrences, column_errors, col4_col5_inconsistencies, bi_sequence_errors


# ============================================================
# Reporting helpers
# ============================================================

def report_invalid_tags(column, regex_valid, tag_counts, tag_occurrences):
    """
    Print invalid tags for a given column with line numbers and content.
    """

    print(f"\n=== INVALID TAGS — COLUMN {column} ===")

    if column not in tag_counts:
        print("Column not present.")
        return

    found = False
    for tag in sorted(tag_counts[column]):
        if not regex_valid.match(tag):
            found = True
            print(f"\nInvalid tag: {tag}")
            for line_number, content in tag_occurrences[column][tag]:
                print(f"  Line {line_number}: {content}")

    if not found:
        print("No invalid tags found.")


# ============================================================
# Main execution
# ============================================================

def main():
    # Run all analyses
    tag_counts, tag_occurrences, column_errors, col4_col5_inconsistencies, bi_sequence_errors = analyse_tsv(FICHIER_TSV)

    # === REPORT 1: Tag distribution ===
    print("\n=== TAG DISTRIBUTION PER COLUMN ===")
    for column in sorted(tag_counts):
        print(f"\nColumn {column}:")
        for tag, count in tag_counts[column].most_common():
            print(f"  {tag}: {count}")

    # === REPORT 2: Invalid tags (regex validation) ===
    report_invalid_tags(4, REGEX_COL4_VALID, tag_counts, tag_occurrences)
    report_invalid_tags(5, REGEX_COL5_VALID, tag_counts, tag_occurrences)
    report_invalid_tags(6, REGEX_COL6_VALID, tag_counts, tag_occurrences)
    report_invalid_tags(7, REGEX_COL7_VALID, tag_counts, tag_occurrences)

    # === REPORT 3: Column count errors ===
    print("\n=== STRUCTURAL ERRORS (COLUMN COUNT) ===")
    if column_errors:
        for line_number, count, content in column_errors:
            print(f"Line {line_number}: {count} columns (expected {NB_EXPECTED_COLUMNS}) → {content}")
        print(f"\nTotal structural errors: {len(column_errors)} lines")
    else:
        print("No column count errors found.")

    # === REPORT 4: Column 4 / 5 entity inconsistencies ===
    print("\n=== COLUMN 4 / COLUMN 5 ENTITY INCONSISTENCIES ===")
    if col4_col5_inconsistencies:
        for line_number, col4, col5, content in col4_col5_inconsistencies:
            print(f"Line {line_number}: Col4='{col4}' vs Col5='{col5}' → {content}")
        print(f"\nTotal column 4/5 inconsistencies: {len(col4_col5_inconsistencies)} lines")
    else:
        print("No entity inconsistencies found.")

    # === REPORT 5: B-I sequence errors ===
    print("\n=== B-I SEQUENCE ERRORS (COLUMNS 4, 5, 6) ===")
    if bi_sequence_errors:
        for line_number, col_index, current_tag, prev_tag, prev_line_number, content in bi_sequence_errors:
            entity_suffix = current_tag[2:]
            expected_tags = f"'B-{entity_suffix}' or 'I-{entity_suffix}'"
            print(f"Line {line_number}, Col {col_index}: Found '{current_tag}' but previous tag (line {prev_line_number}) was '{prev_tag}' (expected {expected_tags})")
            print(f"  → {content}")
        print(f"\nTotal B-I sequence errors: {len(bi_sequence_errors)} lines")
    else:
        print("No B-I sequence errors found.")


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":
    main()