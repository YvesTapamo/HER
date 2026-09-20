# Data profile and observed quality findings

Profile generated from the supplied synthetic files after harmonisation.

| Source | Source shape | Stored facts | Important handling |
|---|---:|---:|---|
| Country A CSV | 2,500 rows | 2,469 | 31 blank amounts quarantined; 13 quoted/thousands amounts normalized; 54 negatives retained and flagged; one duplicated source ID flags both rows; one missing date retained and flagged |
| Country B XLSX | 2,001 expenditure rows + 18 CoA rows | 2,001 | Seven preamble rows skipped; French field names, `DD-MM-YYYY`, decimal-comma and `FCFA` amount variants normalized; CoA sheet loaded |
| Country C JSON | 2,500 parent transactions | 2,624 lowest-grain facts | 59 parents contain 183 child facts; those children replace their parents to avoid double-counting; 216 resulting facts are USD and are not converted; 26 stored facts lack a description |

The resulting database contains 7,094 usable facts, 31 quarantined records, 312 attached quality issues and 2,886 items requiring classification review. Of the usable facts, 5,176 use an explicit country/account rule and 1,918 remain unmapped. Totals are shown independently for KES, XOF, RWF and USD.

## Interpretation cautions

- A negative is not assumed to be wrong: it may be a reversal or credit. It remains in totals and is flagged.
- A repeated transaction ID is not automatically deleted because IDs alone do not prove that two accounting entries are duplicates.
- Capital items and generic overheads are often left unmapped because the supplied simplified SHA functional list does not safely support those assignments.
- Supplier names sometimes conflict with expenditure descriptions; supplier is therefore searchable context, not a classification signal.
- Country C's metadata count describes parents, while the warehouse stores the lowest available grain. Reconciliation must compare child sums to their parents before comparing row counts.

