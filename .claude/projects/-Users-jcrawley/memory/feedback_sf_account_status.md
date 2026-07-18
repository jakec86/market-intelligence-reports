---
name: SF Account_Status__c Unreliable
description: Salesforce Account_Status__c field can be stale — always verify with SBQQ__Subscription__c records before stating account status
type: feedback
originSessionId: d06823ff-f6a5-435e-b515-6079468439c7
---
Do not trust `Account_Status__c` alone to determine if a dealer is a current customer. Always check `SBQQ__Subscription__c` for active subscriptions (where `SBQQ__SubscriptionEndDate__c` is null or in the future).

**Why:** eCarOne (6000362) showed `Account_Status__c = "Prospecting"` but was actually an active customer on Marketplace (Independent Premium+ Listings), Cars Social (6 active subscriptions), and AccuTrade Connected — spending $20K+/year since July 2021.

**How to apply:** When pulling dealer info from Salesforce, always run a second query on `SBQQ__Subscription__c WHERE SBQQ__Account__c = '{AccountId}'` to get actual product subscriptions. Use subscription data as the source of truth for customer status, not the Account status field.

**Confirmed again 2026-04-24:** Dealer Health Dashboard smoke test for Nalley Lexus Galleria showed `Account_Status__c = "Prospecting"` and `Product_Amount__c = 0`, causing Claude to flag the account as a prospect with "$0 in active products" — but Nalley is a current active customer with Price Badge Report workflows, admin.cars.com access, and an AE assigned. **Next fix:** update `dealer_health.py` SF_QUERY to also pull `SBQQ__Subscription__c` records so Claude sees actual products.
