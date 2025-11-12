# NECB Database Validation Report

**Date**: 2025-11-07
**Database**: `/workspaces/bluesky/src/bluesky/mcp/data/necb.db`
**Status**: ⚠️ **CRITICAL DATA QUALITY ISSUES FOUND**

---

## Executive Summary

A comprehensive validation of the NECB database revealed **multiple critical data quality issues** that affect the usability of the data for building energy code compliance calculations:

- **3 CRITICAL ISSUES**: Missing required thermal transmittance data
- **64 Split Tables**: Table numbers with multiple entries (expected for large tables)
- **6 Tables with Empty Data**: Tables containing only empty rows

**Immediate Action Required**: NECB 2017 Table 3.2.2.2 is missing walls/roofs/floors thermal transmittance data.

---

## Critical Issues

### 1. NECB 2017 Table 3.2.2.2 - Missing Above-Ground Opaque Assembly Data

**Severity**: 🔴 **CRITICAL**

**Issue**: The primary table for above-ground thermal requirements is incomplete.

**Details**:
- **Section Reference**: Section 3.2.2.2 "Thermal Characteristics of Above-ground Opaque Building Assemblies"
- **Expected Content**: Walls, Roofs, Floors thermal transmittance values
- **Actual Content**: Only "All fenestration" data (which belongs in Table 3.2.2.3)
- **Impact**: Cannot calculate prescriptive compliance for NECB 2017 wall/roof/floor requirements

**Database Entry**:
```
Table ID: 371
Page: 75
Headers: ['Component', 'HeatingDegree-DaysofBuildingLocation,(1)inCelsiusDegree-Days', ...]
Rows: 3 (should be 5+)
Components Found: ['Allfenestration']  ← WRONG - should be Walls/Roofs/Floors
```

**Comparison with Other Vintages**:
| Vintage | Page | Rows | Components Found |
|---------|------|------|------------------|
| NECB 2011 | 51 | 5 | ✅ Walls, Roofs, Floors |
| NECB 2015 | 73 | 3 | ✅ Walls, Roofs, Floors |
| **NECB 2017** | **75** | **3** | ❌ **Only fenestration** |
| NECB 2020 | 73 | 3 | ✅ Walls, Roofs, Floors |

**Root Cause**: PDF parsing error - likely multi-part table where only fenestration section was captured.

**Remediation**: Re-parse NECB 2017 PDF pages 74-75 to capture complete Table 3.2.2.2.

---

### 2. NECB 2020 Table 3.2.2.2 (FDWR) - Incomplete Data

**Severity**: 🟡 **MODERATE**

**Issue**: FDWR table entry is incomplete, missing lower HDD ranges.

**Details**:
- **Table ID**: 574 (Page 84)
- **Expected**: Complete HDD range from < 4000 to > 7000
- **Actual**: Only partial data starting at 6250 HDD

**Database Entry**:
```
Row data: ['6250\n6500\n6750\n7000\n> 7000', '0.25\n0.23\n0.22\n0.20\n0.20']
Missing: < 4000 through 6000 HDD ranges
```

**Comparison**:
- NECB 2011 FDWR (Table ID 134): 15 rows ✅ Complete
- NECB 2015 FDWR (Table ID 193): 1 row with all HDD ranges ✅ Complete
- NECB 2017 FDWR (Table ID 379): 1 row with all HDD ranges ✅ Complete
- **NECB 2020 FDWR (Table ID 574)**: 1 row with partial data ❌ Incomplete

**Remediation**: Verify if there's another entry with the missing data, or re-parse.

---

### 3. Empty Table Entries

**Severity**: 🟡 **MODERATE**

**Issue**: 6 tables contain only empty row data.

**Affected Tables**:
| Vintage | Table Number | Table ID | Page | Empty Rows | Total Rows |
|---------|-------------|----------|------|------------|------------|
| 2020 | Table-85-4 | 579 | 85 | 21 | 21 |
| 2011 | Table-209-4 | 139 | 209 | 20 | 20 |
| 2015 | Table-87-4 | 198 | 87 | 20 | 20 |
| 2017 | Table-88-4 | 384 | 88 | 20 | 20 |
| 2017 | Table-88-2 | 382 | 88 | 12 | 14 |
| 2020 | Table-85-2 | 577 | 85 | 12 | 14 |

**Impact**: Wasted database space, potential parsing errors

**Remediation**: Investigate if these are intentional (e.g., continuation table markers) or parsing errors. Remove if invalid.

---

## Data Variance Alerts

### Table 3.2.2.2 Row Count Variance

**Issue**: Dramatic row count differences across vintages (4 to 38 rows)

**Analysis**:
- NECB 2011: 38 rows (3 separate table entries: opaque assemblies + intermediate page + FDWR)
- NECB 2015: 22 rows (3 entries: opaque + intermediate + FDWR)
- **NECB 2017: 4 rows** ← Much lower due to missing wall/roof/floor data
- **NECB 2020: 4 rows** ← Lower than expected

**Explanation**: This variance is partially due to split tables across multiple pages, but NECB 2017 and 2020 have suspiciously low counts.

### Table 4.2.1.6 Row Count Variance

**Issue**: Space types table shows 93% reduction from 2011 to 2020

- NECB 2011: 43 rows (3 entries)
- NECB 2020: 3 rows (1 entry)

**Analysis**: This may be intentional restructuring in newer NECB versions, or could indicate missing data. Requires manual verification.

---

## Expected Patterns (Not Issues)

### Split Tables Across Pages

**Finding**: 64 table numbers have multiple database entries

**Explanation**: This is **EXPECTED BEHAVIOR** for large tables that span multiple pages in the PDF. Examples:

- Table 1.3.1.2 (Referenced standards): 4-6 entries across vintages
- Table 5.2.12.1 (HVAC equipment): 6-13 entries (equipment performance tables span many pages)
- Table 5.3.2.8 (Trade-off values): 27 entries (one per HVAC system type)

**Validation**: Split tables should have:
1. Sequential page numbers
2. Related headers (same or continuation)
3. Non-empty data rows
4. Logical content progression

---

## Database Statistics

### Overall Metrics
- **Total Tables**: 687 entries
- **Unique Table Numbers**: 309
- **Tables Spanning Multiple Entries**: 64 (21%)
- **Tables in All 4 Vintages**: 9 (3%)
- **Vintage-Specific Tables**: 205 (66%)

### Per-Vintage Breakdown
| Vintage | Table Entries | Unique Table Numbers |
|---------|---------------|---------------------|
| 2011 | 168 | 128 |
| 2015 | 189 | 139 |
| 2017 | 176 | 133 |
| 2020 | 154 | 127 |

---

## Recommendations

### Immediate Actions

1. **Re-parse NECB 2017 Table 3.2.2.2**
   - Focus on pages 74-75
   - Capture complete wall/roof/floor thermal transmittance data
   - Verify section text references match table content

2. **Verify NECB 2020 FDWR Table**
   - Check if Table ID 574 is a continuation entry
   - Search for another Table 3.2.2.2 entry on pages 83-84
   - Ensure complete HDD range is available

3. **Clean Up Empty Tables**
   - Investigate Table-85-4, Table-209-4, Table-87-4, Table-88-4, Table-88-2, Table-85-2
   - Determine if these should be removed or re-parsed

### Validation Process Improvements

1. **Add Automated Checks**:
   - Validate section text references match table numbers in database
   - Flag tables with row counts <3 for manual review
   - Check for 100% empty row content

2. **Cross-Reference Validation**:
   - Compare table structure (headers, row count) across vintages
   - Flag >50% variance in row counts for same table number

3. **Parsing Quality Checks**:
   - Verify multi-page tables have sequential page numbers
   - Ensure split tables have logical content flow
   - Check for orphaned table fragments

---

## Impact on Bluesky Codebase

### Affected Modules

1. **`src/bluesky/core/necb_fdwr.py`** (proposed)
   - ✅ Can use FDWR data for 2011, 2015, 2017
   - ⚠️ NECB 2020 FDWR data may be incomplete

2. **Above-Ground Wall Conductance Module** (not yet created)
   - ✅ Can use data for 2011, 2015, 2020
   - ❌ **CANNOT use NECB 2017** - data missing

3. **MCP Server Tools**
   - `get_necb_table()` will return incomplete data for NECB 2017 Table 3.2.2.2
   - Users relying on this data for compliance calculations will get incorrect results

### Workarounds

Until database is fixed:

1. **Document limitation** in module docstrings:
   ```python
   def get_wall_uvalue(hdd, vintage="2011"):
       """
       ...
       Args:
           vintage: NECB vintage (2011, 2015, 2020)
                   NOTE: 2017 not supported due to missing data in database
       """
       if vintage == "2017":
           raise ValueError("NECB 2017 wall U-values not available in database")
   ```

2. **Add validation** to MCP server tools to warn users

3. **Consider manual data entry** for NECB 2017 critical tables as temporary fix

---

## Verification Checklist

To verify database fixes:

- [ ] NECB 2017 Table 3.2.2.2 contains "Walls", "Roofs", "Floors" rows
- [ ] NECB 2017 Table 3.2.2.2 has 5+ rows (zones + header + 3 components)
- [ ] NECB 2020 FDWR data includes all HDD ranges (< 4000 through > 7000)
- [ ] NECB 2020 Table 3.2.2.2 FDWR entry has 15 rows or 1 row with complete data
- [ ] No tables with 100% empty rows (except if documented as intentional)
- [ ] Row counts for Table 3.2.2.2 are comparable across 2011/2015/2017/2020

---

## Appendix: Query Examples

### Check Table 3.2.2.2 Completeness
```sql
SELECT t.vintage, t.table_number, t.id, t.page_number,
       COUNT(r.id) as row_count,
       GROUP_CONCAT(DISTINCT json_extract(r.row_data, '$[0]')) as components
FROM necb_tables t
LEFT JOIN necb_table_rows r ON t.id = r.table_id
WHERE t.table_number = 'Table 3.2.2.2.'
GROUP BY t.id
ORDER BY t.vintage, t.page_number;
```

### Find Empty Rows
```sql
SELECT t.vintage, t.table_number, t.page_number,
       COUNT(*) as empty_count
FROM necb_tables t
JOIN necb_table_rows r ON t.id = r.table_id
WHERE r.row_data LIKE '%["", "", ""]%'
   OR r.row_data = '[""]'
GROUP BY t.id
HAVING empty_count > 5
ORDER BY empty_count DESC;
```

### Compare Row Counts Across Vintages
```sql
SELECT table_number,
       SUM(CASE WHEN vintage = '2011' THEN 1 ELSE 0 END) as count_2011,
       SUM(CASE WHEN vintage = '2015' THEN 1 ELSE 0 END) as count_2015,
       SUM(CASE WHEN vintage = '2017' THEN 1 ELSE 0 END) as count_2017,
       SUM(CASE WHEN vintage = '2020' THEN 1 ELSE 0 END) as count_2020
FROM necb_tables
WHERE table_number LIKE 'Table 3.2.%'
GROUP BY table_number
ORDER BY table_number;
```

---

**Generated by**: Claude Code
**Validation Script**: `/workspaces/bluesky/src/bluesky/mcp/validation/validate_necb_db.py` (to be created)
