# Atlas portal — incident response runbook

SYNTHETIC DEMO ONLY. The Atlas service and all targets below are fictional; this document is not live server telemetry.

Atlas is a customer portal. A SEV1 incident means the portal is unavailable for all customers or there is suspected data exposure. A SEV2 incident affects one feature or a subset of customers with a workaround. The incident commander is the on-call Platform engineer. The communications owner is Product Operations.

For SEV1, acknowledge within 10 minutes, create an incident record and publish a first customer status update within 20 minutes. Publish further updates every 30 minutes until recovery. Suspected exposure must also be escalated to Security immediately. Do not include customer personal data or access tokens in status messages.

Recovery is confirmed only after login, account overview and document download checks pass. A post-incident review is due within three working days. Record impact, timeline, contributing factors and assigned corrective actions. The recovery-time target is 60 minutes; it is a target, not a guarantee or evidence of current health.
