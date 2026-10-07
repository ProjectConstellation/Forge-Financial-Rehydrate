-- FORGE Engineering Cell: ticket lifecycle + gated deploys (OPEN → IN_PROGRESS → SUBMITTED → DEPLOYED | ROLLED_BACK | ...)
-- deploy_status: QUEUED | AWAITING_OWNER | APPROVED | DEPLOYING | DEPLOYED | REJECTED | ROLLED_BACK | REBASE_REQUIRED | TESTS_FAILED
-- deploy_class: STANDARD | PROTECTED
ALTER TABLE eng_tickets ADD COLUMN priority TEXT DEFAULT 'normal';
ALTER TABLE eng_tickets ADD COLUMN claimed_ts REAL;
ALTER TABLE eng_tickets ADD COLUMN branch TEXT;
ALTER TABLE eng_tickets ADD COLUMN commit_sha TEXT;
ALTER TABLE eng_tickets ADD COLUMN deploy_status TEXT;
ALTER TABLE eng_tickets ADD COLUMN deploy_class TEXT;
ALTER TABLE eng_tickets ADD COLUMN deploy_log TEXT;
ALTER TABLE eng_tickets ADD COLUMN approved_ts REAL;
ALTER TABLE eng_tickets ADD COLUMN notes TEXT;
