# Payment Setup Recommendation

This project assumes the account owner is likely operating from mainland China unless updated.

## Recommended Order

1. PayPal China
   - Best first setup for small bounties and platforms that only support PayPal.
   - Keep balances low and withdraw after payments settle.
   - Expect cross-border/commercial fees and withdrawal fees.
   - Current status: personal account opened and bank card linked.

2. Payoneer
   - Useful for freelance marketplaces, B2B payouts, and platforms that support Payoneer directly.
   - Better as a marketplace payout account than as a universal bank replacement.

3. Wise
   - Useful as a multi-currency account/transfer rail if your account is eligible for the needed account details.
   - Good backup for receiving or converting supported currencies.

4. Direct bank SWIFT
   - Better for larger payments where a fixed wire fee is acceptable.

5. Crypto wallet
   - Use only when the bounty platform explicitly supports crypto payout and the transfer is legal and documented.
   - Prefer stablecoin payouts such as USDC over volatile assets when available.

## Not First Choice

- Stripe directly under a mainland China personal profile. Stripe account availability is country/region dependent, and mainland China is not a straightforward first setup path.
- GitHub Sponsors as the immediate payout path. Mainland China is not listed in GitHub Sponsors supported receiving regions as of the latest checked docs, while Hong Kong SAR and Macao SAR are listed.
- Borrowed, fake-region, or friend-owned payout accounts. These create account-freeze and compliance risk.

## Owner-Only Setup

The account owner must personally complete identity, bank, tax, PayPal, Payoneer, Wise, crypto wallet, and platform terms steps. Automation should not store identity documents, bank credentials, wallet seed phrases, or payout passwords.

## Current Status

- PayPal China: ready for first small payouts, subject to platform support and PayPal review.
- Payoneer: not set.
- Wise: not set.
- Crypto wallet: not set.

## How Money Reaches PayPal Without Sharing Credentials

Automation should not receive PayPal passwords, card numbers, verification codes, cookies, or recovery information.

For platform bounties, the owner signs in to the bounty platform and links PayPal inside that platform's payout settings. After a PR or report is accepted, the platform pays the linked PayPal account directly.

For direct client payments, the owner can provide only the PayPal receiving email or PayPal.me link when appropriate. This is not the same as sharing login credentials. Prefer platform-managed payout settings for the first payments.
