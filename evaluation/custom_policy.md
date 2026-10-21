# Acme Corp — Cloud Security Policy

## 1. Storage & Encryption
1.1 All S3 buckets must have server-side encryption enabled using KMS.
1.2 All S3 buckets must have access logging enabled.
1.3 All data-storing resources (databases, storage volumes) must be deployed only in us-east-1 or us-west-2.

## 2. Network Access
2.1 Security groups must never allow inbound traffic from 0.0.0.0/0 on port 22.
2.2 Every security group description must follow the format '<team>: <purpose>' so its owner and intent are clear from the console.

## 3. Identity & Access Management
3.1 IAM policies must never grant wildcard (*) actions on wildcard (*) resources.
3.2 Any IAM role named with the 'admin-' prefix must carry an ApprovedBy tag naming the approving security lead.

## 4. Tagging & Cost Attribution
4.1 Every resource must be tagged with a CostCenter value identifying the owning team.
