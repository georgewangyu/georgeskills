# Official capability boundaries

Checked 2026-10-12. Recheck the current
[ManyChat Swagger](https://api.manychat.com/swagger) before acting. Its public
UI loads the [Page API schema](https://api.manychat.com/swagger/compileJson?type=Page_API)
and [Profile API schema](https://api.manychat.com/swagger/compileJson?type=Profile_API).
These are official documentation resources, not dashboard internal endpoints.
Use `https://api.manychat.com` for the documented operations below.

| Intent | Documented surface | Boundary |
|---|---|---|
| Inspect account, flows, growth tools | GET `/fb/page/getInfo`, `/fb/page/getFlows`, `/fb/page/getGrowthTools` | Inventory does not expose flow authoring or publish/stop operations. |
| Invoke an existing automation | POST `/fb/sending/sendFlow` | Body requires integer `subscriber_id` and string `flow_ns`; invokes existing content, not a new flow or comment trigger. Verify channel eligibility. |
| Send content | POST `/fb/sending/sendContent`, `/fb/sending/sendContentByUserRef` | Current documented content schema and channel policy apply; user ref is not a username. Do not substitute these for comment-trigger creation. |
| Find/read contacts | GET `/fb/subscriber/getInfo`, `/fb/subscriber/findByName`, `/fb/subscriber/findByCustomField`, `/fb/subscriber/findBySystemField` | Name searches are capped at 100; custom-field search supports Text/Number. System-field search takes email OR phone. Do not promise a complete export. |
| Create/update unified contacts | POST `/fb/subscriber/createSubscriber`, `/fb/subscriber/updateSubscriber` | Creation uses email, phone, or WhatsApp phone and documented consent fields. No Instagram username/ID creation input in the checked schema. Do not infer social-channel opt-in. |
| Manage tags | GET `/fb/page/getTags`; POST `/fb/page/createTag`; POST `/fb/subscriber/addTag`, `addTagByName`, `removeTag`, `removeTagByName` | Contact tag removal differs from POST `/fb/page/removeTag` or `removeTagByName`, which irreversibly delete the tag across the page and its subscribers. Prefer scoped contact changes. |
| Manage user fields | GET `/fb/page/getCustomFields`; POST `/fb/page/createCustomField`; POST `/fb/subscriber/setCustomField`, `setCustomFields`, `setCustomFieldByName` | Read IDs/types before writing; these operations do not create an email-collection conversation. |
| Manage bot fields | GET `/fb/page/getBotFields`; POST `/fb/page/createBotField`, `setBotField`, `setBotFieldByName`, `setBotFields` | Bot fields are account-level, not per-contact values. |
| Generate template share link | Profile API POST `/user/template/generateSingleUseLink` | Integer `template_id`; separate Profile token. Existing template must be active with single-use sharing enabled. Link expires after first installation; store/redact as a redeemable capability and share only with an approved recipient/destination. |
| Create/edit/install templates, flow nodes, triggers, or publish/stop automations | Signed-in dashboard | No such endpoint in either checked public schema. Generating a template link is not template creation or automatic installation. |

## Access and rate limits

[API token and parameters](https://help.manychat.com/hc/en-us/articles/14959510331420)
documents account Settings → API, flow namespace in the automation URL, and
IDs from contact cards or documented reads. Access depends on the paid plan;
verify availability without upgrading. Separate Profile settings supply the
Profile API token.

The Help Center lists sending at 25 requests/second and system-field lookup at
100; the checked Swagger specifies `sendFlow` at 20/second plus 100 per
subscriber/hour and system-field lookup at 50/second. Use the lower limits
while the discrepancy remains. Other checked limits: ordinary account reads
100/second; flow inventory, account writes, and ordinary contact operations
10/second. These are ceilings, not recommended operating rates. Check each
operation, handle throttling without repeated sends, and avoid high-rate probes.

## Dashboard guides and distinctions

- [Auto-DM links from comments](https://help.manychat.com/hc/en-us/articles/16654065283100-Quick-Automation-Auto-DM-links-from-comments): Quick Builder setup, targeting, optional email/follow-up, edit/update/stop. Opening DM affects opt-in and which later DMs are available.
- [Instagram comments trigger](https://help.manychat.com/hc/en-us/articles/14281316989724-Instagram-Post-and-Reel-Comments-trigger): channel-specific trigger and repeat-comment limitations; check current eligibility before promising sends.
- [Facebook comments trigger](https://help.manychat.com/hc/en-us/articles/14281386567836-Facebook-Comments-Trigger): explicitly excludes retrospective recognition of comments predating setup.
- [Dev Tools basics](https://help.manychat.com/hc/en-us/articles/14281252007580-Dev-Tools-Basics): Public API changes contacts/sends messages; dynamic blocks and external requests integrate with existing automations. They do not establish a general API for authoring automation graphs.

Automation templates, WhatsApp/Meta message templates, and dynamic-block JSON
are different objects. The Profile link endpoint covers an existing automation
template, not creation/approval of WhatsApp message templates. Route unsupported
operations to the dashboard; never extrapolate support from a similarly named
object or third-party integration.
