# Visible Connections Audit — Multi-Group

Audits all active marketplace stores across covered dealer groups and reports the `Visible_Connections_Email__c` checkbox state from `Product_Fulfillment__c`. Goal: confirm the "Visible Connections Email" checkbox is **unchecked (false)** for all active stores.

## Covered Groups

| Group | MA Parent Account ID | CCID | Tableau Store Count |
|---|---|---|---|
| Asbury Automotive Group | `00136000005iBcoAAE` | 539890 | ~79 |
| Herb Chambers | `0015b00001qUFamAAG` | — | ~34 |
| Koons Automotive Group | `0013600000tNKxnAAG` | 5392338 | ~18 |
| Koons Group 2 (sub-root) | `0015b00001qSXtRAAW` | 185555 | included above |
| Larry H. Miller | `0013600000Gfz2RAAR` | — | ~32 |

## What it checks

- **Field:** `Visible_Connections_Email__c` (boolean) on `Product_Fulfillment__c`
- **Filter:** Listing-type Product_Fulfillment records with `Platform_Status__c = 'Fulfilled'`
- **Hierarchy depth:** Covers direct children AND grandchildren (store → sub-group → MA parent)

## Steps

Run one query per group (SOQL does not support multi-root OR across parent traversal in a single query efficiently). Substitute the MA parent ID per group:

```soql
SELECT Account__r.Name, Account__r.CCID__c, Account__r.Parent.Name,
       recordtypename__c, Platform_Status__c, Visible_Connections_Email__c, Phone_Lead_Options__c
FROM Product_Fulfillment__c
WHERE (Account__r.ParentId = '{MA_PARENT_ID}'
       OR Account__r.Parent.ParentId = '{MA_PARENT_ID}')
  AND Platform_Status__c = 'Fulfilled'
  AND recordtypename__c IN (
    'Franchise_Base_Listings', 'Franchise_Preferred_Listings',
    'Franchise_Premium_Listings', 'Franchise_Premium_Plus_Listings',
    'Independent_Base_Listings', 'Independent_Preferred_Listings',
    'Independent_Premium_Listings', 'Independent_Premium_Plus_Listings'
  )
ORDER BY Account__r.Name ASC
```

For Koons, run twice — once with `0013600000tNKxnAAG` and once with `0015b00001qSXtRAAW` — then combine results.

Flag any stores where `Visible_Connections_Email__c = true`. Those need the checkbox manually unchecked via the Product_Fulfillment record edit in SF.

Report: total store count per group, any flagged stores with their SF Account URL.

## Reference

- TabbedFulfillmentScreens URL for any store: `https://cars-commerce.lightning.force.com/lightning/webpage/%2Fapex%2FTabbedFulfillmentScreens%3FcurrentTab%3DphoneEmail%26id%3D{ACCOUNT_ID}`
- `Account_Status__c` is unreliable across all these groups — use `Platform_Status__c = 'Fulfilled'` on Product_Fulfillment as the active-store filter

## Audit History

| Date | Group | Stores Audited | Flagged |
|---|---|---|---|
| 2026-05-15 | Asbury | 55 | 0 (all clean) |
| — | Herb Chambers | pending | — |
| — | Koons | pending | — |
| — | Larry H. Miller | pending | — |
