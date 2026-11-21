# Amader TOWNHALL | Product requirements document

Independent University, Bangladesh (IUB) · Club administration · Programming Club prototype · Revision 1.1

## Contents

- [1 Introduction](#1-introduction)
- [2 Overall description](#2-overall-description)
- [3 Requirements](#3-requirements)
  - [3.1.1 Club and Executive Body Management](#311-club-and-executive-body-management)
  - [3.1.2 Financial and Fund Management](#312-financial-and-fund-management)
  - [3.1.3 Memo Management and Approval](#313-memo-management-and-approval)
  - [3.1.4 Event and Venue Booking Management](#314-event-and-venue-booking-management)
  - [3.1.5 AI-assisted Event Scheduling](#315-ai-assisted-event-scheduling)
  - [3.1.6 AI-assisted Approval Prioritization](#316-ai-assisted-approval-prioritization)
  - [3.1.7 Club Websites and Event Publishing](#317-club-websites-and-event-publishing)
  - [3.1.8 Performance and Legacy Analytics](#318-performance-and-legacy-analytics)
  - [Shared platform requirements](#shared-platform-requirements)
- [Appendix A. Process catalogue](#appendix-a-process-catalogue)
- [Appendix B. End-to-end acceptance](#appendix-b-end-to-end-acceptance)
- [Appendix C. Delivery sequence and policy decisions](#appendix-c-delivery-sequence-and-policy-decisions)
- [Appendix D. Event-permission memo specimen](#appendix-d-event-permission-memo-specimen)

## 1 Introduction

### 1.1 Purpose

A club organizer should be able to follow one event from its first draft through approval, venue confirmation, publication, expenses and handover. DoSA reviewers should be able to answer three questions from that same record. Who can act next? Which version did they approve? Which evidence supports the amount or status shown?

### 1.2 Intended audience

The Townkeepers development team uses this document to implement and test the application. The Division of Student Activities (DoSA), Faculty Advisors and club Executive Body (EB) members use it to validate responsibilities. The course supervisor can trace a demonstrated journey to a requirement and its acceptance result.

### 1.3 Intended use and format

Section 3 states what each feature must do. Appendix A gives each process its actor, trigger, entry condition, ordered steps, alternatives, recovery and final state. Appendix B joins the processes into acceptance scenarios. Use the stable FR, UC and AC identifiers in issues, tests and demonstrations.

This edition keeps the earlier requirement and use-case identifiers. The following workflow decisions come from the project owner for the IUB Programming Club prototype. Use this edition for product behavior when an earlier design document differs. The memo specimen in Appendix D follows the supplied Office Memo image. Requirements use a numbered user story and observable Success and Failure outcomes.

### 1.4 Product scope and success

Deliver eight product features, with shared platform services used across them. An authorized user can follow a memo through both reviews, identify the official reservation for an event, reconcile verified expenses to original receipts, and reproduce a previous EB term’s results after handover. Section 3 and Appendix B define the evidence needed to accept these outcomes.

Institutional policy, real payments, bank transfers, payroll, ticket sales, academic registration and legally certified digital signatures are outside this release. University-controlled event announcements can be copied to configured external destinations. The application’s club pages, calendars, records and files require sign-in.

### 1.5 Risks and controls

- Two reviewers act on the same memo. Save one decision for the active version and stage. Show the losing reviewer the committed outcome.
- Two clubs select the same hall. Treat the search result as provisional and confirm at most one overlapping reservation.
- A receipt, signature or published notice outlives an edit. Link each to the reviewed version and preserve the earlier evidence.
- A delayed email, OCR result or website response makes a screen look successful. Track the business decision and the delivery attempt separately, and show the last confirmed result.
- A leadership change exposes private records or loses unfinished work. Apply dated assignments and explicit handover while preserving historical ownership.

## 2 Overall description

### 2.1 User classes and authority

- **System Admin.** Holds the highest platform role and bootstraps the first DoSA Head and maintains authorized accounts and infrastructure. Signing authority follows the person’s actual assignment.
- **DoSA Head.** Fills the single DoSA role, oversees clubs, reviews the actionable memo queue and signs the final decision after Advisor confirmation.
- **Department Head or additional signer.** Gets access to the specific record and version assigned for signature. The Faculty Advisor identifies extra signers when needed.
- **Faculty Advisor.** Sends the club onboarding spreadsheet to the Head. Reviews the assigned club’s submitted memo version and confirms with an e-signature or returns a reasoned rejection.
- **Club EB member.** Works within active club and term assignments. A designation such as Treasurer describes the appointment. Named privileges govern drafting, booking, finance and publishing.
- **Reader of a club announcement.** An authenticated internal reader sees permitted notices. An external reader can see only the fields sent to an approved destination under that destination’s access policy.

### 2.2 User journeys and handoffs

1. **Establish a club workspace.** System Admin provisions the Head. Authorized staff record the club, term, appointments and grants from reviewed details. Each provisioned person receives an IUB invitation and signs in. A profile correction is pending until the appropriate reviewer decides it.
2. **Obtain permission to run an event.** An EB organizer saves an event and any required budget. They select a DoSA memo template, fill the mandatory fields and send a frozen version to the assigned Advisor. Advisor confirmation routes it to the named additional signers, if any, and then to the DoSA Head. Rejection takes the EB back to a linked editable revision. All required signatures must refer to that new version before approval.
3. **Secure a venue and publish the decision.** An organizer searches or requests recommendations and submits an eligible slot. A DoSA reviewer confirms only after applicable memo and live venue checks. A publisher previews the approved event fields and publishes the eligible version. An external failure leaves the internal outcome visible.
4. **Account for money and close the event.** Finance staff record the allocation and the separately confirmed release. The EB attaches original evidence to each expense. A reviewer verifies, returns or rejects the submitted amount. Event closeout records participation and outcomes. Authorized viewers reconcile reports to source entries and archived terms.
5. **Handle changes after approval.** A material schedule or budget change opens a linked amendment. The current approved version continues to govern. A replacement venue is confirmed atomically with release of the original slot. An authorized cancellation releases the reservation, updates the calendar and notice, and preserves signatures, bills and audit history.

### 2.3 Operating environment

Use Python for application logic, Django for the browser application and authoritative business operations, FastAPI for private assistance endpoints, and PostgreSQL for records and transactions. Use Django templates for the full-stack UI. Develop by writing failing behavior tests before implementation. This stack decision supersedes the provisional TypeScript, React and NestJS paragraph in the earlier SRS §2.3. The bundled SRS records the current choice. Display campus times in Asia/Dhaka. Record each amount’s currency and default to BDT.

### 2.4 Constraints

Apply server-side action and club/term checks to records, files, exports and direct links. Only an authorized person can advance a protected state. A disconnected client can retain recoverable input. Final decisions require a confirmed server write. AI, OCR and external publishing depend on configured integrations. Manual booking, receipt entry and deadline ordering must work through an outage.

### 2.5 Assumptions and dependencies

DoSA supplies the active templates, working days, lead times, venue restrictions and finance rules. IUB supplies eligible account domains and authorized production operators. Optional integrations require a permitted data flow and working credentials. Use clearly identified demonstration policies and synthetic people, receipts and events until the corresponding institutional values are available. Appendix C assigns the unresolved inputs to owners.

### 2.6 Programming Club operating rules

**People and handover.** The demonstration uses the IUB Programming Club, one Club EB workspace, one Faculty Advisor role, the Head as the only DoSA persona, and a System Admin with system-wide management rights. President, Secretary and Treasurer are appointments within that EB workspace. A member may hold multiple appointments. The President takes responsibility for permitted unfinished work at handover. Each person signs in individually. Sharing a persona never means sharing credentials. A department or extra signatory receives only the assigned signing task. Admin manages the platform and can adjust review priority; event authorization still requires the Faculty Advisor and DoSA Head.

**Decide and propose.** The EB decides the event title, proposed date or dates, time, purpose and preferred venue. The EB may inspect the live calendar at this point. The typed event-permission memo may be submitted with that proposed venue. A confirmed booking is unnecessary at this step. The printed To line identifies the intended recipient, while assigned signers determine the workflow. The sample’s routing for facilities support is specific to that request.

**Endorse the event.** The Faculty Advisor reviews the proposal and any requested amount. The Advisor names extra signatories, including the Department Head for department-floor events when required. Each assigned person signs beneath the same frozen version. After those steps, the DoSA Head signs the final event permission. A typed name in Through alone cannot complete a signing task. A returned memo identifies who requested the correction and why. New content requires a new version and fresh signatures.

**Submit the booking form.** After event permission, the EB opens the separate room form. Every classroom request contains event title, club name, filer designation, local date, start and end times and expected headcount. Venue, memo ID and decision history link the two records. A changed material date or venue follows the amendment path before final confirmation.

- **Classroom, 6–9 p.m.** Require Department Head and Faculty Advisor permission for the evening classroom and DoSA booking approval. Existing endorsements can satisfy the room check only when they explicitly cover that room, date and time on the unchanged version.
- **Full-day classroom, Friday or Saturday.** Use the classroom form. The event already has mandatory Advisor and DoSA memo approval. Prototype interpretation of “DoSA, Admin”: the Head and the Admin each record a form approval before the booking becomes Confirmed. The full-day form does not add a routine Department Head step.
- **DMK, MPH or Auditorium.** Use one shared venue form with a venue selector. Require at least 350 expected students. The selected venue’s actual capacity, blocked intervals and confirmed bookings are separate checks. Prototype routing sends the form to the Head for confirmation; the configured venue-owning department endorses it if required. The institution has not named a specific department for that common form.
- **Other classroom times.** Route the form to the DoSA Head. Add department permission when applicable to the floor or requested by the Advisor. If a special route is unclear, leave the request pending for clarification. The calendar marks the venue Booked only after all applicable decisions and a live conflict check.

**Deadline examples.** Use the event’s first local date. A classroom workshop on 18 December has a submission target of 11 December. For an event designated Big on 31 March 2027, the prototype uses 28 February 2027 as the target. Big is a category chosen for review, independent of the 350-student hall threshold. A late flag informs the reviewers; the EB can still submit.

**Two-day availability.** A two-day event can use two daily intervals; overnight occupancy is required only if the organizer requests it. Search both days together for the same venue, capacity and time constraints. Show confirmed reservations as Booked and pending requests separately. A single selection copies the full pair to the proposal or amendment. Confirm the pair in one transaction. When either day conflicts at confirmation, leave both unbooked for that request and suggest another complete pair.

**Year-end reporting.** Count each completed event once for its original EB tenure. Prototype definition of success: completed, an outcome summary has been entered by the EB, and the Advisor has confirmed the success flag. Record reach as Club/Campus, National or International. Unknown values remain visible as missing data. These are proposed reporting definitions for the prototype.

## 3 Requirements

### Workflow states at a glance

- **Memo.** Draft → Pending Advisor Confirmation → Pending Additional Signatures (if required) → Pending DoSA Approval → Approved. Either reviewer may reject at their stage. Rejection enables a linked draft revision. Eligible withdrawals preserve history. An approved version stays authoritative during amendment review.
- **Venue booking.** Pending → Confirmed, Returned for Correction, Declined or Cancelled. A returned request may be corrected and resubmitted. A confirmed booking holds its full interval until cancellation or an atomic replacement.
- **Event.** Draft → Awaiting Approvals → Approved → Completed. Eligible draft, pending and approved events may be cancelled with a reason. A pending amendment is displayed alongside the current approved details.
- **Expense.** Draft → Submitted → Verified, Returned or Rejected. Returned work restarts as a revision. A verified amount changes through a linked adjustment or reversal.
- **Fund release.** Scheduled → Released or Cancelled. Recording the actual amount, date and evidence confirms a release. A later correction keeps the original confirmation visible.
- **Publication.** Unpublished → Publishing → Published per destination. Track later updates or withdrawals separately. An external failure records the last known delivered version and allows the applicable retry.

### 3.1 Functional requirements

Each numbered feature contains individually testable functional requirements. The shared platform requirements apply across all eight. Each requirement names the relevant processes in Appendix A. A passing test must verify the user-visible result and, for writes, the resulting records and side effects.

#### 3.1.1 Club and Executive Body Management

Provision people and hand over club work without losing its original owner. See processes UC-01 through UC-08.

##### 3.1.1.1 Sign in with an IUB Google account (FR-IAM-01)

As an authorized user, I want to sign in with my Independent University, Bangladesh (IUB) Google account so I can access my workspace.

**Success**

- I select Continue with Google and complete Google's sign-in. The application verifies the result on its server and matches my verified IUB email to one active profile.
- Once the match is verified, the application opens my session. Signing out ends that session.
- A previously provisioned and active user can start a new session after signing out or after session expiry by completing IUB sign-in again.
- The supplied address iub@gmail.com is an example for an explicitly provisioned test account. Institutional eligibility for live use must be configured separately.

**Failure**

- In live mode, an invalid sign-in, personal Google account, or email without an active profile is denied. The error does not reveal whether a profile exists.
- An expired or revoked session cannot reach protected pages or actions.
- If Google sign-in is cancelled, unavailable, or returns an unverifiable result, no application session is created. The sign-in screen remains available for a fresh attempt.
- The example address never enables sign-in for the whole gmail.com domain.

Processes: [UC-01](#uc-01-sign-in-with-iub-google-and-end-a-session).

##### 3.1.1.2 Assign persona, scope and privileges (FR-IAM-02)

As an account administrator, I want to give each user the right club scope and privileges so their workspace matches their responsibilities.

**Success**

- I select an access category such as System Admin, Division of Student Activities (DoSA) Head, designated signer, Club Executive Body (EB) member, or Faculty Advisor. I separately type the actual designation, such as Club Treasurer.
- I use checkboxes to grant access to named modules and actions, such as viewing club finance or submitting an expense. DoSA profiles show N/A for club affiliation. EB members and Faculty Advisors receive access only to their active club assignments.
- Protected pages, records, files, and server actions check the user's access category, active assignment, and granted privileges.
- When a user's active grants change, the next protected action reflects the updated scope, including on an already-open page.
- Use one shared EB interface. President, Secretary and Treasurer are typed appointments. Seed one incumbent per designation per club and term. One person may hold multiple distinct appointments. The President receives unfinished club work at handover. Student on Duty (SOD) is an optional designation.

**Failure**

- A typed designation or a module checkbox alone does not grant an action outside the user's role. Faculty Advisor confirmation and DoSA Head memo approval are restricted to those actors.
- The server denies a direct request to another club's private record or an action the user lacks permission to perform.
- An unrecognized grant or a club assignment that does not apply to the selected role is rejected. An empty grant set gives no module access.
- A second active holder of the same single-holder position is flagged. An account with multiple appointments signs only a step assigned to its authenticated identity.

Processes: [UC-01](#uc-01-sign-in-with-iub-google-and-end-a-session), [UC-02](#uc-02-provision-accounts-and-control-assignments).

##### 3.1.1.3 Create, activate and deactivate profiles (FR-IAM-03)

As an authorized account administrator, I want to create, update, activate, and deactivate profiles so only eligible people can sign in and use their assigned modules.

**Success**

- A System Admin creates the first DoSA Head profile. After setup, the System Admin or the DoSA Head can manage other supported profiles.
- For club provisioning, the Faculty Advisor emails the DoSA Head a spreadsheet containing member details and requested module access. The administrator reviews it and enters the approved information in the application.
- The form collects full name, access category, typed designation, and club affiliation. Department and Major have separate dropdowns with N/A where applicable, including non-student or SOD profiles as appropriate.
- Separate fields collect IUB email, personal email, personal phone, emergency phone, permanent address, and temporary address. The administrator uses checkboxes to choose allowed modules and actions.
- When a profile is created, its owner receives sign-in instructions at their IUB address only. Deactivation ends active access and preserves submissions, decisions, signatures, and audit records.
- A previously deactivated profile can be reactivated by an authorized administrator after checking its role and assignments. It retains its original history.

**Failure**

- Missing required fields, invalid formats, and duplicate IUB addresses are identified before a profile can be saved.
- Delegated staff cannot grant privileges outside their authority. A deactivated profile cannot continue using the application.
- If profile creation succeeds but invitation delivery fails, staff can inspect and retry the IUB email under FR-COM-02 without creating another profile.

Processes: [UC-02](#uc-02-provision-accounts-and-control-assignments).

##### 3.1.1.4 Link access to a term or Faculty Advisor assignment (FR-IAM-04)

As an authorized account administrator, I want to bind club access to an EB term or Advisor assignment so permissions follow the person's appointment dates.

**Success**

- An EB account is linked to its club and term. A Faculty Advisor is linked to the club or clubs they advise. Each assignment records a start date and an end date when known.
- After one assignment ends, any other active assignments keep their own permissions. Earlier work remains attributed to the person, club, and original EB term.
- An assignment becomes effective on its recorded start date. Ending one club assignment leaves unrelated active grants in place.

**Failure**

- An ended assignment no longer authorizes access, including through previously saved links.
- An end date before the start date is rejected. Pending and expired assignments do not authorize actions for that club.

Processes: [UC-02](#uc-02-provision-accounts-and-control-assignments).

##### 3.1.1.5 View profiles and request changes (FR-IAM-05)

As a signed-in user, I want to view my profile and propose corrections so the information accurately reflects my details.

**Success**

- The Profile tab shows identity, designation, affiliation, academic details, contacts, and access details. The pen icon beside a field opens a form for the proposed value.
- A valid request is marked Pending. The Head, as the sole DoSA persona, receives the in-app notification and can approve an ordinary detail correction. The system applies it once and records the old and new values, reviewer, and decision time.
- Requests concerning the IUB sign-in address, role, club assignment, tenure, or privileges route to an administrator authorized for that field. I can see the decision in my Profile tab.

**Failure**

- Invalid proposed values are flagged. The saved value and permissions stay in effect while a request is pending or after it is declined.
- A profile correction cannot bypass the account and assignment controls in FR-IAM-02 through FR-IAM-04.
- If a request has already been decided or its saved field changed during review, a second reviewer sees the current value and decision before any further change can be applied.

Processes: [UC-03](#uc-03-view-profile-and-request-corrections).

##### 3.1.1.6 Open a role dashboard (FR-IAM-06)

As a signed-in user, I want a dashboard for my role so I can find permitted modules, records, and outstanding work.

**Success**

- My dashboard and navigation show modules and actions I can use. The DoSA Head can see permitted club management, memo approvals, venue requests, finance, queues, and reports. The prototype has a single DoSA workspace held by the Head.
- EB members see permitted club memos, bookings, budgets, and notices. Faculty Advisors see assigned clubs, memos awaiting their confirmation, and relevant event updates.
- Dashboard items show status and last update and open their underlying records after an access check.
- A dashboard with no eligible items shows an empty state. Authorized navigation remains available.

**Failure**

- An out-of-scope item is hidden. Opening its link directly does not bypass access checks.
- If access to an item was withdrawn after the dashboard loaded, opening it refreshes the scope check and denies access.

Processes: [UC-04](#uc-04-use-role-dashboard-and-follow-notifications).

##### 3.1.1.7 Authorize and record administrative actions (FR-IAM-07)

As an authorized administrator, I want administrative actions checked and recorded so I can make valid changes and trace who made them.

**Success**

- Account provisioning, club and venue changes, financial confirmations, expense decisions, and other administrative actions check the specific privilege involved.
- The DoSA Head alone makes the final memo decision after Faculty Advisor confirmation. The audit record identifies the individual account, action, affected record, time, and relevant prior and new values.

**Failure**

- An unauthorized action is denied even if the user opens its link directly or changes their displayed designation.
- If an administrative update cannot be saved with its required history, the action fails and the previous state is retained.

Processes: [UC-02](#uc-02-provision-accounts-and-control-assignments), [UC-22](#uc-22-confirm-approve-or-reject-a-submitted-memo).

##### 3.1.1.8 Configure administrative settings (FR-IAM-08)

As the DoSA Head, I want to configure workflow settings so the application uses the applicable lead times, calendars, and venue rules.

**Success**

- I can set submission lead times, working-day calendars where needed, venue restrictions, and eligible notification preferences. Each saved version records the editor and effective date.
- A memo already in review keeps its submission-time memo rules unless an authorized restart is recorded. Final venue confirmation uses current availability and restrictions for the requested interval.
- An eligible future-dated rule version takes effect on its recorded date. The earlier version remains available for audit and any in-flight memo still governed by it.

**Failure**

- Invalid settings are rejected. Settings cannot remove required memo stages or notification recipients.
- A failed settings save leaves the previously effective rules in force.

Processes: [UC-05](#uc-05-configure-administrative-workflow-rules).

##### 3.1.1.9 Maintain the official club register (FR-CLB-01)

As the DoSA Head, I want to maintain an official club register so current and historical records stay linked to the right club.

**Success**

- In Club Management, I can enter and update the official name, institutional profile, and operational status. The system keeps the same club ID across name changes and EB terms.
- Archive preserves earlier terms, events, memos, and financial records for users with the corresponding access.

**Failure**

- An archived club cannot start new requests. A user without permission cannot edit official identity or status.
- If an archive operation fails, the club's current status is retained. Earlier records are not removed by archiving or by a failed archive attempt.

Processes: [UC-06](#uc-06-maintain-club-register-and-internal-club-profile).

##### 3.1.1.10 Create and close EB terms (FR-CLB-02)

As the DoSA Head, I want to record and close EB terms so appointments and access reflect the current leadership period.

**Success**

- I select the club, enter dates, set status, and associate appointed members. The term list identifies current, upcoming, and past terms.
- Closing a term ends the linked access through FR-IAM-04 and preserves its historical records.
- An upcoming term can be recorded before the current term closes without giving the incoming members early access.

**Failure**

- Missing or overlapping dates are flagged. Contradictory active terms are blocked unless an approved transition period is recorded.
- Inconsistent start and end dates prevent activation.

Processes: [UC-07](#uc-07-manage-eb-terms-appointments-and-handover).

##### 3.1.1.11 Appoint EB members and record positions (FR-CLB-03)

As the DoSA Head, I want to appoint provisioned EB members to positions so the club's current responsibilities are clear.

**Success**

- I select the term and member, type the position title and responsibilities, and set effective dates. Term history records the editor and appointment dates.
- The member acts within the module and action privileges granted to their account.

**Failure**

- Duplicate or overlapping appointments are identified before the change is finalized. Typing a title does not grant new access.
- An appointment outside a term's recorded dates or to an ineligible profile is returned for correction before it can grant access.

Processes: [UC-07](#uc-07-manage-eb-terms-appointments-and-handover).

##### 3.1.1.12 View the club organogram (FR-CLB-04)

As an authorized DoSA, EB, or Faculty Advisor user, I want to see a club organogram so I can identify its current or previous leadership.

**Success**

- The organogram opens to the current term and shows recorded members and their positions. Choosing a past term displays its dates, structure, and historical label.

**Failure**

- A viewer without access to a club or restricted member field cannot see that information.
- If a club has no recorded current term, the page identifies the missing term and still allows the user to view any authorized history.

Processes: [UC-08](#uc-08-view-current-organogram-and-legacy-eb-archive).

##### 3.1.1.13 Browse and correct the EB archive (FR-CLB-05)

As an authorized club records user, I want to find previous EB terms so I can review earlier members, events, and achievements.

**Success**

- The archive supports browsing or searching by club and term. Authorized DoSA corrections record the previous value, editor, reason, and time. Closed terms retain their earlier links.
- A search with no matching archive records shows an empty result. The reviewer can change the club or term filter.

**Failure**

- A missing historical detail displays Not recorded. A correction cannot silently overwrite the previous record.
- A correction submitted against a superseded archive version requires the editor to review the latest record before retrying.

Processes: [UC-08](#uc-08-view-current-organogram-and-legacy-eb-archive).

##### 3.1.1.14 Record a leadership handover (FR-CLB-06)

As the DoSA Head, I want to record a leadership handover so the incoming EB can continue designated work.

**Success**

- I select the outgoing and incoming terms, effective date, and eligible unfinished memos, events, or reports for transfer.
- The system retains original authorship and term attribution. It separately records work done by a member of the incoming term.

**Failure**

- Incoming members cannot act on unfinished items outside their authorization or on items whose current status no longer permits action.
- If a selected item is completed, archived, or otherwise becomes ineligible before the handover is saved, it cannot transfer as unfinished work.

Processes: [UC-07](#uc-07-manage-eb-terms-appointments-and-handover).

##### 3.1.1.15 Maintain the internal club profile (FR-CLB-07)

As an authorized EB member, I want to update my club's internal profile so permitted users have current information.

**Success**

- I can edit my club description and designated internal contacts. The club page is available to authorized signed-in club members and DoSA Head.

**Failure**

- EB edits cannot change official identity or status. The public and other unauthorized viewers cannot open the internal page or see its protected member, memo, or financial details.
- Invalid contact details or edits to a club outside the user's assignment are rejected. A public preview does not expose the internal club profile.

Processes: [UC-06](#uc-06-maintain-club-register-and-internal-club-profile).

#### 3.1.2 Financial and Fund Management

Follow the money from a club allocation to an event’s verified expenses. See processes UC-09 through UC-17.

##### 3.1.2.1 Record allocations by funding period (FR-FIN-01)

As an authorized DoSA finance user, I want to record club funding allocations by period so the club can see how much funding was assigned.

**Success**

- I choose the club and funding period and enter the amount, currency, date, and source. BDT is selected by default, and the system records the actual currency and creator.
- The club finance view shows the allocation and reporting period. Changes to approved allocations retain the previous amount and audit history.

**Failure**

- A negative allocation amount is rejected.
- An allocation linked to a missing club or funding period cannot be saved. Repeating a failed submission does not create a second amount for the same operation.

Processes: [UC-09](#uc-09-record-allocations-and-fund-release-status).

##### 3.1.2.2 Schedule and confirm fund releases (FR-FIN-02)

As an authorized DoSA finance user, I want to schedule, confirm, or cancel fund releases so club users can see which amounts were actually released.

**Success**

- I link a release to a club and funding period. It appears as Scheduled. A permitted user records the actual amount, date, and confirmation reference or evidence to mark it Released.
- A scheduled release can be cancelled with a recorded reason. EB users with finance access see Scheduled, Released, or Cancelled for their club.

**Failure**

- A release stays unconfirmed without the required amount, date, and confirmation information. Payments themselves take place outside the application.
- A cancelled release cannot be marked Released. A correction to a confirmed release is made through a linked adjustment or reversal.

Processes: [UC-09](#uc-09-record-allocations-and-fund-release-status).

##### 3.1.2.3 View club funding and recorded balance (FR-FIN-03)

As an authorized DoSA finance or EB user, I want to see my selected club's recorded balance so I can distinguish funds released from amounts still scheduled.

**Success**

- The view shows allocations, scheduled releases, net confirmed releases, verified expenditure, and the recorded balance for the selected club and period. Figures link to their underlying entries.
- The balance is confirmed inflows minus verified outflows. Each linked adjustment is applied once. The view identifies the reporting period and currency.
- A recorded zero and an unrecorded value are shown distinctly. When there are no qualifying entries in the selected scope, the view identifies that condition.

**Failure**

- Scheduled and cancelled releases are excluded from confirmed inflows. Different currencies are shown separately unless a conversion rate and record are available.
- A missing conversion rate leaves the amounts separate. An unverified or rejected expense cannot reduce verified funds.

Processes: [UC-10](#uc-10-review-club-funding-overview).

##### 3.1.2.4 Prepare and revise an event budget (FR-FIN-04)

As an EB user with the appropriate finance privilege, I want to prepare and revise an event budget so DoSA can review projected costs for the event.

**Success**

- I add line items with descriptions, quantities or units where applicable, and planned amounts. The budget links to its event and applicable memo.
- Saving a revision keeps the earlier version and identifies changed line items. DoSA can open the relevant version for review.
- The EB types any positive requested amount with its currency and purpose. The Faculty Advisor reviews it and either endorses it for the next finance step or returns it with feedback. The approved request and actual release remain separate.

**Failure**

- A user without budget-editing access cannot save a new version. A revision does not replace the historical budget version.
- If a line amount is invalid or the event link is outside the user's scope, the system identifies the issue. A failed or concurrent save does not corrupt another budget version.
- An unreviewed request does not advance as Advisor-endorsed. A high amount alone cannot trigger an invented maximum.

Processes: [UC-11](#uc-11-prepare-and-revise-event-budget).

##### 3.1.2.5 Compare planned and verified event spending (FR-FIN-05)

As an authorized DoSA finance user, I want to compare planned and verified event spending so I can identify and review variances.

**Success**

- The comparison names the budget version and shows planned cost, verified expenditure, and the difference calculated as verified expenditure minus planned cost.
- A positive difference is labelled Over budget, with links to the underlying records.
- A zero variance indicates matching planned and verified amounts. A negative variance indicates spending below the planned amount.

**Failure**

- Unverified expenses are excluded from verified spending. An over-budget warning does not make a financial approval or disciplinary decision.
- If no applicable budget exists, the view identifies the missing comparison basis rather than comparing against an assumed zero.

Processes: [UC-12](#uc-12-review-budget-against-verified-expenditure).

##### 3.1.2.6 Create and submit an expense (FR-FIN-06)

As an EB user with finance write access, I want to submit an expense with its supporting evidence so DoSA can review it.

**Success**

- I choose an event from my club or a permitted general-expense category and enter amount, currency, date, description, and supporting reference.
- The system records the submitter, expense ID, and status. Once required fields and evidence pass validation, the expense appears in the DoSA queue as Submitted.

**Failure**

- Negative amounts, links to another club's event, and missing required information block submission. Refunds and corrections use linked adjustments.
- If the supporting evidence upload fails, an expense requiring it cannot advance. Repeating a submitted request does not create a second expense.

Processes: [UC-13](#uc-13-record-expense-and-attach-original-receipt).

##### 3.1.2.7 Attach and inspect original bills (FR-FIN-07)

As an authorized EB expense submitter or DoSA reviewer, I want to attach or view the original bill so the expense has traceable evidence.

**Success**

- The EB user can add a bill image or PDF to the expense. The system checks its type and size and links the original file for authorized review.
- the DoSA Head can open the original from the review screen. Corrected or replacement evidence preserves the earlier file in the record history.
- Keep the shopkeeper’s receipt (“shop memo”) as original expense evidence. If it is missing, save the expense as awaiting evidence and send the EB a warning with a reviewer-set deadline. After upload, route it for normal verification.

**Failure**

- An unsupported or oversized file is rejected. An unauthorized user cannot retrieve the original.
- An interrupted upload can be retried. It does not replace earlier evidence or satisfy the evidence requirement until a valid file is available.
- On expiry, mark the evidence overdue and keep the claim outside verified spending. A partial release or missing receipt cannot silently make the expense verified.

Processes: [UC-13](#uc-13-record-expense-and-attach-original-receipt).

##### 3.1.2.8 Extract receipt details with OCR (FR-FIN-08)

As an authorized EB member, I want to extract receipt details with optical character recognition (OCR) so I can prepare an expense without typing every field.

**Success**

- Where OCR is enabled, I can request extraction from the receipt view. Suggested vendor, date, amount, and readable line items appear beside the original with an Unverified label.
- I can correct or confirm suggested fields for submission. Expense verification still requires the DoSA decision in FR-FIN-10.

**Failure**

- If OCR is disabled, unavailable, or unable to read the file, the application shows that outcome and permits manual entry. The original remains retrievable.
- If extraction returns only part of a receipt or an apparent mismatch, the user can inspect the original, complete missing fields, and correct suggestions before sending them for review.

Processes: [UC-14](#uc-14-run-ocr-and-review-potential-duplicate-flags).

##### 3.1.2.9 Flag possible duplicate or inconsistent bills (FR-FIN-09)

As a DoSA finance reviewer, I want possible duplicate or inconsistent bills to be flagged so I can inspect the evidence before deciding.

**Success**

- The review shows the reason and permitted matching evidence for exact file matches or likely matches based on vendor, date, reference, or amount. It also flags differences from an available readable receipt total.

**Failure**

- A flag does not verify or reject an expense. A case with incomplete match information remains subject to human review.
- If two receipts look similar but are distinct, the reviewer can proceed based on the evidence. Missing data cannot support a definitive duplicate decision.

Processes: [UC-14](#uc-14-run-ocr-and-review-potential-duplicate-flags).

##### 3.1.2.10 Verify, return or reject an expense (FR-FIN-10)

As an authorized DoSA finance reviewer, I want to verify, return, or reject an expense so its outcome and evidence can be traced.

**Success**

- I review the expense and original evidence and select Verify, Return, or Reject. The system records reviewer, time, decision, and any required comments.
- An authorized EB submitter can revise a returned expense in a new draft. A verified expense correction uses FR-FIN-13. Prior decisions, amounts, and evidence remain traceable.

**Failure**

- Returning or rejecting without a reason is blocked. A verified amount cannot be silently overwritten.
- If the record changes before a reviewer commits a decision, the reviewer is shown the current revision. Only one valid decision for the original state is recorded.

Processes: [UC-15](#uc-15-verify-return-reject-or-correct-expense).

##### 3.1.2.11 View an event cash flow ledger (FR-FIN-11)

As an authorized DoSA finance user, I want an event cash flow ledger so I can reconcile recorded inflows with verified event costs.

**Success**

- I can record an event inflow with an event reference and supporting source. If it is already recorded, I link the attribution to the same source entry.
- The ledger shows confirmed event inflows, verified expenses, adjustments, and net cash flow, calculated as confirmed event inflows minus verified event outflows after corrections. Entries link to source records and show verification status.

**Failure**

- General club allocations remain outside event inflows. Unverified figures appear separately, and absent amounts or sources display Not recorded.
- If the existing inflow is already attributed to the same event, another link cannot count it twice. A receipt outside the reviewer's permission is excluded from drill-down.

Processes: [UC-16](#uc-16-inspect-event-cash-flow-ledger-and-bills).

##### 3.1.2.12 Export financial records (FR-FIN-12)

As an authorized DoSA finance user, I want to export a filtered financial report so I can review or share the totals within the permitted scope.

**Success**

- I choose club, period, currency, and status. The export uses the same records, totals, and access checks as the filtered view and records its scope, currency, and generation time.
- The export states whether it includes unverified entries and labels them separately from verified totals.

**Failure**

- Records or links outside the exporter's permissions are excluded.
- An invalid filter or failed export displays the problem without returning a misleading partial report. An empty valid result identifies its scope and lack of matching records.

Processes: [UC-17](#uc-17-export-scoped-financial-records).

##### 3.1.2.13 Apply financial corrections consistently (FR-FIN-13)

As an authorized DoSA finance reviewer, I want to record a correction or reversal so totals change while the original transaction remains traceable.

**Success**

- A confirmed correction is recorded separately with a source transaction, amount, reason, reviewer, and time. Fixed decimal precision is used to calculate the updated club and event totals.
- Reports count the original and its adjustment once each. The original is available for inspection.
- The EB records an unused amount or refund, links the original release or expense and attaches its explanation. The Advisor reviews the reconciliation. Record the authorized correction once before changing totals.

**Failure**

- Repeating the same correction does not create another effective adjustment. Corrections do not overwrite the original verified record.
- An adjustment without an eligible source transaction or required details is rejected. A failed save leaves both source history and totals consistent.
- An unreviewed refund or unused-funds entry cannot silently reduce verified expenditure or imply a payment.

Processes: [UC-09](#uc-09-record-allocations-and-fund-release-status), [UC-15](#uc-15-verify-return-reject-or-correct-expense).

#### 3.1.3 Memo Management and Approval

Move one immutable submission through the Advisor and Head decisions. See processes UC-18 through UC-26.

##### 3.1.3.1 Create and choose memo templates (FR-MEM-01)

As the DoSA Head, I want to maintain reusable memo templates so EB authors can start drafts with the correct fields and signature areas.

**Success**

- In the DoSA workspace, I can create, edit, activate, or deactivate a template. It includes a DoSA-assigned label, labelled information boxes, required fields and attachments, and e-signature areas for the Faculty Advisor and DoSA Head.
- Users with memo access can open Memo Management from the left navigation. EB authors see active templates by label and select one to start a draft.
- A template change creates a new version. Existing memos keep the template version they used.
- Offer one event-permission memo type for the Programming Club. Version changes update this type. The separate room-booking form is selected later under FR-EVT-05.

**Failure**

- An inactive template does not appear in the new-draft choices. A user without template-management permission cannot change a template.
- A template missing required stage or signature areas cannot be activated. A saved draft created before deactivation retains its original template.
- The power-support example’s recipient, personnel, school and dates are never copied as default club details.

Processes: [UC-18](#uc-18-create-and-version-memo-templates).

##### 3.1.3.2 Author and save a memo draft (FR-MEM-02)

As an authorized EB author, I want to save and reopen a memo while I prepare it so I can complete the information at my own pace.

**Success**

- During Authorship, I select a template and link an event. The draft shows the configured information boxes, applicable budget reference, and attachment fields. Saving preserves its contents and files for reopening.
- The initial draft and any new revision started after rejection remain editable during Authorship.
- Type the memo text manually: school and department if applicable, To (recipient and designation), Through (Advisor name and designation plus any instructed routing), From, memo date, subject, body and contact if supplied. Include event title, dates, start/end times, purpose and proposed venue in the body. The event link identifies the record. No memo content is calculated or prefilled.

**Failure**

- Once sent to the Faculty Advisor, the submitted version is read-only during both review stages and after approval.
- If a newer draft was saved while I was editing, the system warns me before an overwrite.
- If saving fails, the memo does not enter a review queue. Recoverable text and accepted attachments remain available for retry.
- Display a recipient guidance prompt when preparing To and Through. A draft may be saved with incomplete routing, but submission requires the recipient designation, Advisor name and designation, and event details.

Processes: [UC-19](#uc-19-draft-and-save-a-structured-memo).

##### 3.1.3.3 Complete the memo information (FR-MEM-03)

As an EB author, I want the memo to show the required information and attachments so I know what to complete before handing it over.

**Success**

- The draft marks required fields and attachments. It can be saved while incomplete.
- When I send the memo, the system checks the applicable event and budget links and the permitted attachment types and sizes. The Faculty Advisor receives the version after it passes these checks.
- When a template has no required budget reference or attachment, the author can advance without that item if all applicable checks pass.

**Failure**

- Missing fields, invalid links, and unsupported files are identified by the relevant input. The memo stays in Authorship until required corrections are made.
- An attachment whose upload failed or an event outside the author's club cannot satisfy a required field.

Processes: [UC-19](#uc-19-draft-and-save-a-structured-memo).

##### 3.1.3.4 Confirm a memo with an e-signature (FR-MEM-04)

As a Faculty Advisor or DoSA Head, I want my e-signature to identify the exact memo version I reviewed so others can trace my decision.

**Success**

- The assigned Faculty Advisor opens the EB's submitted version, adds an e-signature, and selects Confirm. The system records the Advisor account, signature, version, action, and time.
- At DoSA Approval, the DoSA Head adds their own e-signature before approving. A revised version collects fresh signatures in the applicable stages.
- Every designated signatory can draw their own e-signature underneath the memo body in their labelled block. Store signer, designation, date/time, decision and version. Proposed prototype convention: add department and other signer blocks only when assigned.

**Failure**

- Confirmation or approval is blocked if the required signature or other approving information is missing.
- An earlier signature cannot serve as confirmation of a revised version.
- If a signature is added to a version that was replaced or the signing action cannot be saved, the system leaves the stage unchanged and displays the current status.
- An unrelated person cannot sign just because they can see the memo. A withheld endorsement keeps the Head’s approval unavailable.

Processes: [UC-20](#uc-20-record-a-reviewer-e-signature-for-a-memo-version), [UC-22](#uc-22-confirm-approve-or-reject-a-submitted-memo).

##### 3.1.3.5 Validate each stage before sending the memo forward (FR-MEM-05)

As an EB author or memo reviewer, I want the system to check the information required for my stage so the memo advances only after I complete my part.

**Success**

- At Authorship, Send to Faculty Advisor checks the required fields, attachments, event and other linked details, and applicable lead time.
- At Faculty Advisor confirmation and DoSA approval, the system checks the actor's assignment or privilege, the current version, preceding stage, and required information and signature. Advisory messages are labelled as warnings.
- A warning can be shown without blocking the next stage if every mandatory check passes.

**Failure**

- A blocking issue identifies the field or prerequisite and leaves the memo at the current stage.
- A rejection is blocked until the reviewer provides the reason required by FR-MEM-08. An approving signature is required only for confirmation or approval.
- A missing required signature or preceding decision blocks advancement. A short submission lead time flags the memo as late and leaves the decision to reviewers.

Processes: [UC-21](#uc-21-validate-and-send-a-memo-to-the-faculty-advisor).

##### 3.1.3.6 Send the memo and record submission (FR-MEM-06)

As an EB author, I want to send a completed memo to the Faculty Advisor and track its handoff so I know when it reaches each queue.

**Success**

- Send to Faculty Advisor freezes the current version, records the EB author and server time, marks the memo Pending Advisor Confirmation, and notifies the assigned Advisor.
- After Advisor confirmation and completion of all required endorsements, the system records DoSA queue entry and marks the version Pending DoSA Approval.

**Failure**

- Repeated clicks or retries record only one transition for that version and stage.
- A failure before the handoff is committed leaves the version in its prior stage. A notification failure after a committed handoff is handled under FR-COM-02.

Processes: [UC-21](#uc-21-validate-and-send-a-memo-to-the-faculty-advisor), [UC-22](#uc-22-confirm-approve-or-reject-a-submitted-memo).

##### 3.1.3.7 Route the memo through the three stages (FR-MEM-07)

As a memo participant, I want the system to route the memo through the correct people so I can tell who needs to act next.

**Success**

- The three main stages are EB Authorship, Faculty Advisor Confirmation (including any required departmental or additional endorsements before handoff), and DoSA Head Approval.
- The memo identifies the next actor, enables the next action after the preceding stage is complete, and shows both reviewers the same frozen version.
- The Advisor identifies any Department Head or other necessary signer before confirming. The Head receives the memo after all required signers have endorsed it. A department-floor event uses the Department Head when that permission applies.

**Failure**

- A reviewer cannot act out of sequence, outside their assigned club or authority, or on a superseded version.
- If the assigned reviewer is unavailable or has lost access, the memo remains at its current stage until an eligible reviewer can act. The system does not skip that stage.
- An additional signer may return the version with a reason. Notify the author and Advisor, keep the evidence, and restart review on a linked corrected version.

Processes: [UC-22](#uc-22-confirm-approve-or-reject-a-submitted-memo).

##### 3.1.3.8 Approve or reject a memo (FR-MEM-08)

As an assigned Faculty Advisor or the DoSA Head, I want to record my memo decision and explain a rejection so the EB can address it.

**Success**

- The DoSA Head selects Approve after e-signing. At their review stage, the Advisor or Head can select Cancel to open Reject Memo, enter a short reason, and explicitly confirm the rejection.
- A DoSA Head rejection sends the EB author, assigned EB participants, and Faculty Advisor an in-app notice and IUB email with the reason and memo link.
- An Advisor rejection sends the EB author and assigned EB participants the notice and IUB email. The DoSA Head sees the rejection in memo tracking and receives no rejection email for this path.
- The decision saves the stage, version, reviewer, time, outcome, and any required rejection reason.

**Failure**

- A rejection without a reason or explicit confirmation is blocked. An obsolete or already-decided version cannot accept another decision.
- If two decisions are attempted on the same memo stage, the system keeps the first successfully committed decision. A delayed or failed rejection email does not undo the saved rejection.

Processes: [UC-22](#uc-22-confirm-approve-or-reject-a-submitted-memo).

##### 3.1.3.9 Edit and resubmit a rejected memo (FR-MEM-09)

As an EB author, I want to correct and resubmit a rejected memo so reviewers can decide on the revised version.

**Success**

- I open the Rejected memo using View, read the reason, and start a new editable revision. The rejected version, reason, dates, and signatures remain in history.
- I send the corrected version to the assigned Advisor. It follows the applicable stage checks and signature sequence before a new DoSA Head decision.
- The new attempt is linked to the original memo and has its own submission and decision history.

**Failure**

- While a review is pending, the existing submitted version cannot be edited. Old signatures cannot be applied to the new version.
- If the resubmission fails validation, the revision stays editable and the earlier rejection remains in history.

Processes: [UC-23](#uc-23-revise-and-resubmit-a-rejected-memo).

##### 3.1.3.10 View pending work and memo progress (FR-MEM-10)

As a memo participant, I want to see pending memos and their progress so I know the current stage and any action required from me.

**Success**

- Memo Management shows each accessible memo's label and status. The statuses include Draft, Pending Advisor Confirmation, Pending DoSA Approval, Rejected, Approved, and Withdrawn.
- I can find pending items and use View to see the current stage, responsible actor, and permitted history. The EB and Faculty Advisor can see applicable rejection reasons, and the DoSA Head can see rejection history in the tracking dashboard.
- If there are no pending items in the user's scope, the view says so and allows access to authorized history.

**Failure**

- Internal DoSA notes are withheld from users without the corresponding privilege. Memos outside a user's scope are inaccessible.
- If an item changed status after the list loaded, View shows the current status rather than relying on the old dashboard label.

Processes: [UC-24](#uc-24-track-memo-status-and-review-history).

##### 3.1.3.11 Track submission, deadline and event dates (FR-MEM-11)

As an assigned reviewer, I want to see when a memo was sent, when approval is due, and when the event starts so I can plan the review.

**Success**

- The system stores the handoff to the Faculty Advisor, entry into the DoSA queue, approval deadline, and planned event start as separate dates or timestamps.
- Reviewers see the relevant dates and available review time. Authorized changes to the deadline or event date recalculate that time and preserve the original submission timestamps.
- The reviewer can still inspect the original handoff and queue-entry times after a deadline change.
- For a workshop or classroom event, flag submission less than seven calendar days before the first event date. For an event marked Big, use one calendar month before that date. Big takes precedence. Use Asia/Dhaka local dates and clamp month-end to the last valid day.

**Failure**

- Missing or invalid deadlines are flagged. A different date is not substituted for the approval deadline.
- An already-passed deadline is shown as overdue under FR-AIP-04. A stale date change cannot overwrite a newer saved date without review.
- A late memo shows the required submission date and warns that permission may be declined. Do not automatically reject or approve it.

Processes: [UC-21](#uc-21-validate-and-send-a-memo-to-the-faculty-advisor), [UC-24](#uc-24-track-memo-status-and-review-history).

##### 3.1.3.12 Request an amendment after approval (FR-MEM-12)

As an EB author, I want to propose a material amendment to an approved memo so I can request new approval for changes to the event.

**Success**

- A separate amendment action starts a linked draft that follows Authorship, Advisor Confirmation, and DoSA Approval. The system shows the approved details and proposed changes separately.
- Revised dates, venues, budgets, and notices take effect after the applicable memo, venue, and publication checks pass.

**Failure**

- The original approved memo remains read-only. Pending or unsuccessful amendments do not replace approved event details.
- If an amendment is rejected, withdrawn, or blocked by a required booking check, the current approved version remains in use.

Processes: [UC-25](#uc-25-initiate-an-amendment-to-approved-memo-content).

##### 3.1.3.13 Withdraw a request or export a memo (FR-MEM-13)

As an authorized EB author, I want to withdraw an eligible memo or export a copy so I can close an unused request or retain its record.

**Success**

- Withdrawing an eligible draft or pending memo with a reason sets it to Withdrawn and preserves its history.
- Exporting an accessible version includes its template label, status, recorded signatures, and export date.
- Provide an English A4 preview and export using the editable text and recorded signature blocks in Appendix D. Preserve the line order, paragraph breaks and the status of the exact version.

**Failure**

- A withdrawal without a reason or from an ineligible status is blocked. Changes to approved events follow the amendment or cancellation process.
- A version the author cannot view cannot be exported.
- If withdrawal races with a final review decision, the system applies only the valid transition saved first. An export failure produces no completed export.
- A draft preview cannot display a signature or approval that has not been recorded.

Processes: [UC-26](#uc-26-withdraw-an-eligible-memo-or-export-a-version).

#### 3.1.4 Event and Venue Booking Management

Request, confirm and release venue time while keeping event approval visible. See processes UC-27 through UC-34.

##### 3.1.4.1 Create an event record (FR-EVT-01)

As an authorized EB organizer or DoSA Head, I want to create an event record so I can manage its schedule and related requests in one place.

**Success**

- An EB organizer creates an event from their club workspace. the DoSA Head can create central events. The form collects title, type, description, organizer, contact, dates and times, and the owning club or DoSA.
- The saved event receives an ID and shows its status, linked memo, budget, booking requests, and documents as they are added.
- An event may be saved as a draft before its memo, budget, or venue request is added.

**Failure**

- Invalid dates or an organizer outside the permitted scope block creation.
- An end time at or before the start time, or an event submitted to the wrong club, cannot be saved as valid.

Processes: [UC-27](#uc-27-create-event-and-manage-controlled-event-changes).

##### 3.1.4.2 Change event details (FR-EVT-02)

As an event organizer, I want to edit a draft or propose changes to an approved event so I can keep its details current.

**Success**

- An authorized organizer can save edits to a draft. Changing an approved event's schedule, venue, budget, or other approval-sensitive detail starts an amendment showing current and proposed values.
- The system shows which memo and booking checks apply to the amendment.

**Failure**

- Pending or unsuccessful amendments do not replace the approved details shown on event and publication pages.
- If a draft changes before another editor saves, the newer version is retained. An approved schedule or venue cannot be overwritten by a pending amendment.

Processes: [UC-27](#uc-27-create-event-and-manage-controlled-event-changes).

##### 3.1.4.3 Maintain the venue catalogue (FR-EVT-03)

As an authorized DoSA venue manager, I want to maintain the venue catalogue so users can find suitable venues for their events.

**Success**

- I can add or edit a venue's name, location, capacity, type, facilities, operating hours, and active status. Permitted users can search and filter the catalogue.
- Inactive venues remain linked to earlier records.

**Failure**

- An inactive venue is unavailable for new requests. Changes to capacity and operating rules require the venue-management privilege.
- Invalid capacity or operating-hour details are returned for correction. Existing bookings remain traceable when the venue details change.

Processes: [UC-28](#uc-28-administer-venues-central-events-and-restricted-hours).

##### 3.1.4.4 Search venue availability (FR-EVT-04)

As an authorized organizer, Faculty Advisor, or DoSA user, I want to search venue availability so I can identify a suitable time and place.

**Success**

- I can search by date, time, capacity, and intended use. Results distinguish free slots, pending requests, confirmed reservations, and unavailable intervals.
- A Pending label identifies a request still in review. The interval stays unreserved until confirmation.
- Different venues may be available during the same interval. With no matching slots, the search returns an empty result and allows the filters to be changed.

**Failure**

- A closure or restricted interval appears as unavailable. The search does not reveal another club's private booking or event details.
- Availability can change after results load. A listed slot still goes through live submission and confirmation checks.

Processes: [UC-29](#uc-29-search-venue-availability).

##### 3.1.4.5 Submit a venue booking request (FR-EVT-05)

As an authorized EB organizer, I want to submit a venue request for an event so DoSA can review my preferred time and location.

**Success**

- I choose the venue and date, enter start and end times, setup and cleanup time, and any required justification. The request links to the event and description and to the approved event-permission memo for a club event.
- The system checks whether the venue is active and whether the full interval meets capacity, closure, and restricted-hour rules. A club event with an approved memo may lodge its eligible form as Pending. Competing pending requests are highlighted.
- Use the approved memo to start a separate classroom form. Require event title, club name, filer designation, date, start/end time and expected headcount. For MPH, DMK and Auditorium use one common large-venue form with a venue selector and at least 350 expected students.

**Failure**

- An invalid time range, inactive venue, failed capacity check, closure, restricted time, or confirmed overlap blocks submission.
- If a slot becomes restricted or confirmed after selection but before submission, the system shows the live conflict and does not create an eligible pending request for it.
- At 349 expected students, a large-venue request fails the stated minimum. At 350 it can proceed if actual capacity and other checks pass. A proposed venue on a memo does not reserve a room.

Processes: [UC-30](#uc-30-submit-a-venue-booking-request).

##### 3.1.4.6 Detect overlapping intervals (FR-EVT-06)

As an organizer or venue reviewer, I want conflicts shown for the full booking interval so setup and cleanup time are accounted for.

**Success**

- For the same venue, intervals overlap when each starts before the other ends. The check includes setup and cleanup buffers. Adjacent intervals are allowed when their full intervals do not overlap.
- The availability and review screens distinguish conflicts with pending requests from conflicts with confirmed reservations.
- Identical, partial, and contained intervals for one venue are all detected as overlaps. An adjacent interval becomes a conflict when its buffers overlap.

**Failure**

- An overlap shows the affected time and only the details the viewer is permitted to see. A pending conflict does not appear as a confirmed reservation.
- An interval ending at or before it starts is flagged as invalid rather than included as a conflict-free booking.

Processes: [UC-29](#uc-29-search-venue-availability), [UC-30](#uc-30-submit-a-venue-booking-request).

##### 3.1.4.7 Confirm a conflict free reservation (FR-EVT-07)

As an authorized DoSA venue reviewer, I want confirmation to recheck the latest schedule so conflicting reservations cannot both succeed.

**Success**

- Confirm checks the venue's active status and capacity, the requested times and buffers, confirmed reservations, closures, restricted hours, and applicable memo prerequisites.
- When the checks pass, the booking confirmation and reservation of the interval are saved together.
- Use the routing rules in §2.6. For an evening classroom, check the Advisor and Department Head permissions before DoSA confirms. For a full-day Friday or Saturday classroom, record the DoSA and Admin decisions on the separate form. Reuse signatures referencing an unchanged approved event where applicable.

**Failure**

- If simultaneous confirmations overlap for one venue, at most one succeeds. The other remains unconfirmed and shows the conflict.
- A repeated confirmation does not create another reservation.
- If saving the reservation fails after validation, no confirmed status or partial reservation remains. A retry checks current availability again.
- A missing route-specific decision leaves the reservation unconfirmed. If the venue or approved schedule changes materially, check the amendment before booking.

Processes: [UC-31](#uc-31-review-and-confirm-a-venue-booking).

##### 3.1.4.8 Review and decide a booking request (FR-EVT-08)

As an authorized DoSA venue reviewer, I want to decide a pending booking request so organizers know whether their preferred slot is available to them.

**Success**

- The review shows the event details, linked memo status, applicable Faculty Advisor and DoSA decisions, and scheduling checks. I can select Confirm, Return for Correction, or Decline.
- The system records the reviewer, action, time, and reason where required. The organizer sees the result separately from the memo decision.
- A return for correction keeps the review reason and history, and the organizer can submit an eligible corrected request after validation.

**Failure**

- Confirm is blocked if an applicable memo decision is missing or the live checks in FR-EVT-07 fail.
- Return and Decline require a reason before the decision can be saved.
- A booking that was already decided or superseded cannot be decided again from a stale review page.

Processes: [UC-31](#uc-31-review-and-confirm-a-venue-booking).

##### 3.1.4.9 Reschedule or cancel a booking (FR-EVT-09)

As an authorized event organizer, I want to reschedule or cancel a booking so the schedule reflects when I need the venue.

**Success**

- A change to date, time, or venue opens a linked Pending request. Once approved and checked against other active reservations, the new reservation and release of the original interval are saved together.
- An authorized cancellation records a reason and releases the interval. The view retains earlier requests and shows the current reservation or cancellation.

**Failure**

- A pending or unsuccessful replacement leaves the original reservation in effect. A cancellation without the required reason is blocked.
- If the replacement conflicts or fails to save, the original reservation and related event information stay in effect.

Processes: [UC-32](#uc-32-reschedule-or-cancel-venue-booking).

##### 3.1.4.10 Show the internal event calendar (FR-EVT-10)

As a user with calendar access, I want to view and filter internal events so I can find the dates and bookings relevant to me.

**Success**

- The calendar offers month, week, and event-list views and filters for club, venue, date, and status. Draft, pending, approved, and cancelled entries are labelled separately.
- Selecting an entry opens its event if I have the required access.

**Failure**

- A user outside the event's scope cannot view its private details or draft.
- If filters match no visible events, the view shows an empty state rather than exposing excluded or inaccessible events.

Processes: [UC-33](#uc-33-view-event-calendar-and-separate-approval-states).

##### 3.1.4.11 Add central activities and venue blocks (FR-EVT-11)

As the DoSA Head, I want to add central activities or block a venue so it is unavailable when the university needs it.

**Success**

- I can enter a central event or create a block for maintenance, closure, or institutional use. A block records the venue, time interval, and reason.
- The venue schedule checks blocks and central activities alongside club bookings.

**Failure**

- An interval overlapping a confirmed reservation shows the conflict for DoSA to resolve through rescheduling or cancellation.
- An invalid or reversed block interval is rejected. A closure does not silently cancel an already confirmed reservation.

Processes: [UC-28](#uc-28-administer-venues-central-events-and-restricted-hours).

##### 3.1.4.12 Show separate event, memo and booking statuses (FR-EVT-12)

As an event participant, I want to see the event, memo, and booking statuses separately so I know which approvals are outstanding.

**Success**

- The event detail page shows overall status, linked memo status, booking status, confirmed location when available, and outstanding actions.
- Event states distinguish Draft, Awaiting Approvals, Approved, Completed, and Cancelled. A pending amendment is shown separately from the currently approved details.

**Failure**

- The event cannot become Approved while an applicable memo or venue prerequisite remains incomplete.
- If memo, booking, or amendment information is pending or declined, the event page identifies what remains unresolved and preserves the separate statuses.

Processes: [UC-33](#uc-33-view-event-calendar-and-separate-approval-states).

##### 3.1.4.13 Apply restricted hours in Dhaka time (FR-EVT-13)

As an authorized DoSA venue manager, I want to set restricted hours so venue requests follow campus scheduling rules in Dhaka time.

**Success**

- I can set or update restrictions for one venue or all venues and record the effective period. Events and reservations display in the Asia/Dhaka time zone.
- The system checks the full interval of manual requests and suggested slots, including overnight periods, multi-day periods, and booking buffers.
- An interval that touches the end of a restriction is eligible if its buffers and remaining checks also pass.

**Failure**

- An overlap with restricted hours blocks the request or confirmation and identifies the affected date and time.
- If restriction settings change before final confirmation, the requested interval is checked against the currently effective rules.

Processes: [UC-28](#uc-28-administer-venues-central-events-and-restricted-hours).

##### 3.1.4.14 Complete or cancel an event (FR-EVT-14)

As an authorized organizer, I want to complete or cancel an event so the event record, booking, and notices reflect its actual outcome.

**Success**

- I can mark an approved event Completed and record its outcome. To cancel an eligible event, I provide a reason and confirm the action.
- Cancellation closes active booking requests, releases reservations, and marks or withdraws internal calendar entries and notices according to the publication setting.
- The event retains its memo, budget, expenses, receipts, and audit history.

**Failure**

- An ineligible status or missing cancellation reason prevents the corresponding action.
- If cancellation cannot save its required internal updates together, the prior state remains. If a separate external publication update fails after internal cancellation, it is visible and retryable under FR-PUB-07.

Processes: [UC-34](#uc-34-complete-or-cancel-an-event).

#### 3.1.5 AI-assisted Event Scheduling

Find feasible slots and carry a chosen suggestion into the normal booking process. See processes UC-35.

##### 3.1.5.1 Request scheduling suggestions (FR-AIS-01)

As an EB organizer with scheduling access, I want to request suggestions based on my event needs so I can find potential venues and times.

**Success**

- I enter event type, preferred dates, expected attendance, duration, and setup needs. I can also enter optional venue or time preferences.

**Failure**

- Missing required details or an impossible combination of dates and duration is identified before the request runs. I can correct my inputs and retry.
- A date range or venue preference that yields no valid candidates offers a revised search. A request outside the user's scheduling scope is denied.

Processes: [UC-35](#uc-35-request-advisory-ai-scheduling-recommendations).

##### 3.1.5.2 Screen suggestions against booking rules (FR-AIS-02)

As an EB organizer, I want suggestions checked against booking rules so I can concentrate on slots I may actually request.

**Success**

- Candidates are checked against confirmed reservations, closures, restricted hours, capacity, permitted use, and required preparation and approval lead times.
- Only candidates that pass those checks appear as recommendations.

**Failure**

- When no slot passes, the system explains that no candidate fits and lets me adjust the inputs.
- Suggestions with missing or inconsistent scheduling data are omitted. A service response cannot make an ineligible interval valid.

Processes: [UC-35](#uc-35-request-advisory-ai-scheduling-recommendations).

##### 3.1.5.3 Compare suggested venues and times (FR-AIS-03)

As an EB organizer, I want to compare recommended venues and times so I can choose an appropriate alternative.

**Success**

- Each recommendation shows venue, date, time, and an availability label. If the requested date or slot is unavailable or restricted, eligible alternatives appear when available.

**Failure**

- If no alternative fits, the system gives a brief explanation and offers manual venue search.
- If availability changes while the list is open, a selected option still goes through the current booking checks and cannot bypass a newly applicable conflict.

Processes: [UC-35](#uc-35-request-advisory-ai-scheduling-recommendations).

##### 3.1.5.4 Use a suggested slot in a request (FR-AIS-04)

As an EB organizer, I want to copy a suggested slot into my booking request so I can submit it through the normal process.

**Success**

- Selecting a suggestion fills the venue and times in the booking form for my review. The application rechecks availability and restrictions at submission and DoSA confirmation.
- The organizer can review and edit prefilled details before submitting them for the same validation used by a manually entered request.
- When a requested two-day event conflicts, offer pairs of consecutive dates in the same eligible venue and daily time window. One click selects both slots and opens the prefilled proposal or reschedule flow. Show both dates and current Booked or Pending labels.

**Failure**

- If a slot has become ineligible, the application shows the conflict and blocks submission or confirmation. Selecting a suggestion alone does not reserve the venue.
- Never offer a half-available pair. Recheck both intervals on confirmation. If either is now unavailable, reserve neither and retain the original booking on a failed reschedule.

Processes: [UC-35](#uc-35-request-advisory-ai-scheduling-recommendations).

##### 3.1.5.5 Limit the data used by AI assistance (FR-AIS-05)

As an organizer using scheduling assistance, I want the service to receive only the details it needs so club records remain protected.

**Success**

- If the scheduling service is enabled, its request contains the needed event and venue information, such as date range, duration, capacity, and availability.
- When another club's reservation affects eligibility, the service receives only the blocked venue interval. The application records the request reference, outcome, and fallback status.

**Failure**

- Another club's private event and memo details, receipts, financial evidence, and personal member records are excluded from the service request.
- A response containing fields beyond the scheduling task does not expose protected records or change permissions. A failed service call leaves the manual workflow available.

Processes: [UC-35](#uc-35-request-advisory-ai-scheduling-recommendations).

##### 3.1.5.6 Continue scheduling when AI is unavailable (FR-AIS-06)

As an EB organizer, I want to continue searching and requesting venues when scheduling assistance is unavailable so my event planning can continue.

**Success**

- Manual venue search remains available, and an eligible slot chosen manually follows the normal request flow.
- A later successful recommendation can be requested independently without changing manually submitted or confirmed records.

**Failure**

- A timeout, failed request, or unusable suggestion shows a message and offers manual search. Existing bookings and reservations keep their current state.

Processes: [UC-35](#uc-35-request-advisory-ai-scheduling-recommendations).

#### 3.1.6 AI-assisted Approval Prioritization

Help the Head choose the next actionable memo and explain its urgency. See processes UC-36.

##### 3.1.6.1 Use separate dates for priority (FR-AIP-01)

As the DoSA Head, I want to see the individual dates used for priority so I can understand how much time a memo has for review.

**Success**

- The queue uses separate submission time, approval deadline, event start, and preparation lead time. I can view those inputs for each applicable memo.

**Failure**

- A missing or invalid approval deadline is flagged at the relevant field. The system does not use the event date in its place.
- An invalid or incomplete timing field is identified separately from a passed deadline. Missing data is not given a fabricated priority.

Processes: [UC-36](#uc-36-review-and-manually-order-approval-priority-queue).

##### 3.1.6.2 Prioritize actionable requests (FR-AIP-02)

As the DoSA Head, I want actionable memos ranked by urgency so I can focus on the requests that need attention first.

**Success**

- The queue ranks requests awaiting my decision using time to the approval deadline and then event start as the secondary ordering key. Identical dates use queue-entry time and stable memo ID. Enabled AI ranking uses the same recorded timing information.
- The calculation records its time and inputs. Changing the event date, deadline, policy, or request status triggers a new calculation.
- The standard queue uses approval deadline first, then event date/time. Admin may record a reasoned queue override. The queue shows both dates and the actor who must decide.

**Failure**

- A memo that is no longer awaiting a DoSA Head decision does not remain in the actionable ranking.
- If a priority computation is stale after a deadline or status change, the queue shows the applicable fallback under FR-AIP-06.
- Changing priority confers no right to sign another actor’s decision.

Processes: [UC-36](#uc-36-review-and-manually-order-approval-priority-queue).

##### 3.1.6.3 Explain the displayed priority (FR-AIP-03)

As the DoSA Head, I want each queue priority explained so I can understand what drove the suggested order.

**Success**

- A row shows priority, approval deadline, time remaining, and contributing factors. A processing-time estimate is identified as an estimate and shows the configured review window used.

**Failure**

- The ranking cannot approve or reject a memo. Decisions are recorded in Memo Management by the authorized reviewer.
- If ranking factors are missing or stale, the view flags the result and offers the deadline order under FR-AIP-06.

Processes: [UC-36](#uc-36-review-and-manually-order-approval-priority-queue).

##### 3.1.6.4 Distinguish overdue and insufficient time (FR-AIP-04)

As the DoSA Head, I want overdue and short-lead-time cases identified so I can recognize relevant timing problems before making a decision.

**Success**

- A passed approval deadline is marked Overdue. A past event start is identified separately. Each warning shows the relevant date.
- If available time falls below the applicable review or preparation threshold, the queue shows the time remaining and the threshold.
- If an item is both overdue and past its event date, both conditions can be seen separately.

**Failure**

- A timing warning leaves the review decision to the DoSA Head and cannot approve or reject the memo.

Processes: [UC-36](#uc-36-review-and-manually-order-approval-priority-queue).

##### 3.1.6.5 Filter and adjust queue order (FR-AIP-05)

As the DoSA Head or System Admin, I want to filter or reorder actionable requests so I can manage the review queue.

**Success**

- I can filter the queue or move an item up or down. An override records my account, reason, prior order or score, and expiry or removal.

**Failure**

- Queue changes cannot change signatory authority, memo status, or approval prerequisites. Users without the queue-management privilege cannot reorder items.
- An expired override or an override for a request that is no longer actionable stops affecting the active queue.

Processes: [UC-36](#uc-36-review-and-manually-order-approval-priority-queue).

##### 3.1.6.6 Fall back to deadline ordering (FR-AIP-06)

As the DoSA Head, I want a usable review queue when priority calculation is stale or unavailable so I can keep processing requests.

**Success**

- The queue can display earliest-deadline-first order and flag requests without a deadline. On refresh it shows the current calculation time and inputs.
- After service recovery, the queue recalculates from current inputs before displaying a refreshed priority.

**Failure**

- A failed or stale result is labelled. The system uses deadline order and keeps standard memo actions available.
- If no actionable requests exist, the queue shows an empty state. If deadlines are unavailable, those items remain visible with a missing-deadline label.

Processes: [UC-36](#uc-36-review-and-manually-order-approval-priority-queue).

#### 3.1.7 Club Websites and Event Publishing

Control which approved event details appear at each publishing destination. See processes UC-37 through UC-39.

##### 3.1.7.1 Check publication eligibility (FR-PUB-01)

As an event publisher, I want the system to check that an event is ready to publish so users receive approved information.

**Success**

- An EB publisher can select Publish for their own club. The DoSA Head or System Admin can publish across clubs. The system checks the approved event version, required memo approval, and any required venue confirmation.
- An eligible publication records the publisher and destination. Internal pages require sign-in. External publishing follows FR-PUB-04.

**Failure**

- A missing approval, unconfirmed required venue, or unauthorized publisher blocks publication.
- A publisher cannot use an outdated preview to publish after the event becomes ineligible or its approved version changes.

Processes: [UC-37](#uc-37-preview-and-publish-approved-internal-event-notice).

##### 3.1.7.2 Preview the event notice (FR-PUB-02)

As an authorized publisher, I want to preview a notice for its destination so I can confirm what will be shown.

**Success**

- The preview shows the approved event title, schedule, venue, organizer, description, and approved media. Pending details are identified separately.

**Failure**

- Missing required fields are flagged. Private memos, budgets, receipts, and member contacts are excluded from external previews and outgoing content.
- If the selected destination or approved version changes, the preview is refreshed before publication so the outgoing content still matches its destination.

Processes: [UC-37](#uc-37-preview-and-publish-approved-internal-event-notice).

##### 3.1.7.3 Display notices on authorized internal pages (FR-PUB-03)

As an authorized DoSA, EB, or Faculty Advisor user, I want to see published internal notices so I can follow events in my permitted scope.

**Success**

- A published notice appears on the relevant club page and links to the authenticated event calendar entry. The notice and entry use the same event ID.
- The EB can publish ordinary club announcements to its own page. The DoSA Head and System Admin may target any club or all internal club pages. Approved-event notices additionally follow FR-PUB-01.

**Failure**

- An unauthenticated or out-of-scope request is denied without revealing protected event details.
- If a notice has been withdrawn, its previous link does not continue serving the notice. Cancelled notices follow the selected publication settings.
- An EB account cannot select another club or All clubs. An ordinary announcement cannot advertise an unapproved event as approved.

Processes: [UC-37](#uc-37-preview-and-publish-approved-internal-event-notice).

##### 3.1.7.4 Publish to a configured external website (FR-PUB-04)

As an authorized publisher, I want to send an approved event notice to a supported club website so it can also appear there.

**Success**

- When DoSA has approved and configured the connection, I can send permitted publication fields as a separate external operation. The integration uses the destination's supported create, update, or withdrawal actions.

**Failure**

- If the connection is unavailable or the attempt fails, the system shows its outcome. The internal event and its access controls remain in effect.
- A missing connector or unsupported external action is identified without marking the external operation successful.

Processes: [UC-38](#uc-38-publish-event-to-configured-external-website).

##### 3.1.7.5 Use a single approved event version (FR-PUB-05)

As an event publisher, I want each destination to use the approved event version so the event details agree across views.

**Success**

- The internal calendar and club notice reference the same approved event version. A configured external destination receives approved publication fields from that version.
- An approved amendment applied to an existing internal notice updates the notice and published calendar entry together.

**Failure**

- A pending amendment does not replace published details.
- A delayed update for an older version cannot replace a newer published notice. External delivery failures remain visible separately from the current internal version.

Processes: [UC-37](#uc-37-preview-and-publish-approved-internal-event-notice), [UC-39](#uc-39-update-or-withdraw-published-event-notice).

##### 3.1.7.6 Update or withdraw a published notice (FR-PUB-06)

As an authorized publisher, I want to update or withdraw a published notice so it reflects an approved change or cancellation.

**Success**

- I can update the approved details, mark the internal notice Cancelled, or withdraw it according to publication settings. Earlier actions remain in history.
- A configured external website receives the corresponding update or withdrawal where supported.

**Failure**

- If external synchronization fails, its status is shown separately from the internal publication state.
- An unapproved amendment cannot update a notice. An unsuccessful external withdrawal remains visible separately and can be retried if the destination supports it.

Processes: [UC-39](#uc-39-update-or-withdraw-published-event-notice).

##### 3.1.7.7 Inspect and retry external publication (FR-PUB-07)

As an authorized publisher, I want to inspect and retry external publication so I can resolve a failed attempt without creating a duplicate notice.

**Success**

- The publishing view shows each destination's latest attempt time and outcome, last successful update, and available error. A retry updates an existing destination record where applicable.

**Failure**

- A failed attempt remains marked unsuccessful until success is confirmed. Retrying does not create a duplicate notice.
- If the destination has an uncertain outcome after a timeout, a retry uses the existing publication reference where available. It does not report success until confirmed or create a duplicate notice.

Processes: [UC-38](#uc-38-publish-event-to-configured-external-website), [UC-39](#uc-39-update-or-withdraw-published-event-notice).

#### 3.1.8 Performance and Legacy Analytics

Compare terms and trace each count or amount to its records. See processes UC-40 through UC-44.

##### 3.1.8.1 Find event cards by club (FR-ANL-01)

As the DoSA Head, I want to browse a club's event cards so I can locate the event I need to review.

**Success**

- I choose a club and search or filter by term, date, type, and status. Each card shows the event name, key dates, approval status, and publication status.
- Selecting a card opens the corresponding event record.
- The view identifies when no events match the selected filters and allows another selection within the user's scope.

**Failure**

- A club or event outside my permissions does not appear in results.

Processes: [UC-40](#uc-40-browse-club-event-cards-and-open-event-workspace).

##### 3.1.8.2 Open the event workspace (FR-ANL-02)

As an authorized event reviewer, I want one workspace for event records so I can follow relevant information from the event summary.

**Success**

- The workspace shows the summary and permitted links to the memo, venue request, cash flow, participation, and attachments.

**Failure**

- A missing field or record displays Not recorded. The available sections and statuses remain visible, and restricted links are withheld.
- If a linked item is removed from the viewer's scope between opening the workspace and following the link, the underlying access check denies it.

Processes: [UC-40](#uc-40-browse-club-event-cards-and-open-event-workspace).

##### 3.1.8.3 Check bills and OCR from the event workspace (FR-ANL-03)

As an authorized DoSA finance user, I want to inspect bills and OCR details from the event workspace so I can check the original evidence.

**Success**

- An expense opens its linked receipt image or PDF with vendor, amount, expense review status, and available extraction details.
- Suggested OCR values and human-reviewed values have distinct labels.

**Failure**

- If OCR results are unavailable, the original receipt and any recorded review status remain available. Preview or download is denied when the current permission check fails.
- If the original file is unavailable, the screen identifies it as unavailable and still shows authorized expense and review details.

Processes: [UC-16](#uc-16-inspect-event-cash-flow-ledger-and-bills), [UC-41](#uc-41-inspect-source-receipts-and-ocr-in-event-analytics).

##### 3.1.8.4 Record attendance and achievements (FR-ANL-04)

As an authorized EB organizer, I want to record attendance and achievements so the club can report event outcomes.

**Success**

- I select the event and applicable EB term, then enter the attendance measure, method, and supporting source or note. I can record an achievement with a description and event or term reference.
- Recorded counts, estimates, and verification status are labelled.

**Failure**

- Missing attendance displays Not recorded and remains distinct from a measured count of zero.
- Attendance that is invalid for the applicable measure or a term reference outside the event's scope is flagged for correction.

Processes: [UC-42](#uc-42-record-event-participation-and-achievements).

##### 3.1.8.5 Compare EB terms (FR-ANL-05)

As the DoSA Head, I want to compare EB terms so I can understand event activity across different leadership periods.

**Success**

- I select a club and terms. The comparison shows term dates and explains event and work attribution across terms, including the original term preserved at handover.
- Raw totals are shown separately from normalized rates. When terms differ in length, a rate shows the applicable period or denominator.
- For the selected EB tenure report distinct completed events, completed events marked successful, and completed national or international events. Each total opens its contributing event list. Record event reach and the EB’s outcome summary at closeout.

**Failure**

- The comparison does not treat raw counts from unequal terms as normalized rates.
- A rate with no valid denominator or insufficient source data is unavailable. The comparison identifies the missing basis.
- Exclude drafts and cancellations from completed counts. Missing outcome or reach stays Unknown. Preserve the original EB term attribution across handover.

Processes: [UC-43](#uc-43-compare-eb-performance-and-inspect-metric-sources).

##### 3.1.8.6 Define reporting measures (FR-ANL-06)

As a report viewer, I want to see how measures are defined so I can interpret the club's reported performance correctly.

**Success**

- The performance view states definitions, included statuses, and date ranges for event counts, completed events, verified expenditure, released funds, and budget variance. Financial measures follow the finance calculations.
- The system counts valid current entries and accepted corrections for the selected scope.

**Failure**

- Each measure shows whether incomplete or unverified data is excluded or displayed separately. Superseded values are not counted again.
- If source inputs are incomplete, the measure retains its stated scope and identifies the limitation rather than presenting an unsupported result.

Processes: [UC-43](#uc-43-compare-eb-performance-and-inspect-metric-sources).

##### 3.1.8.7 Filter trends and open source records (FR-ANL-07)

As the DoSA Head, I want to filter trends and open the underlying records so I can explain a reported total.

**Success**

- I can filter by club, EB term, event period, and event status. Charts and tables use the same settings.
- Selecting a total opens its permitted event or financial records and displays the active filters needed to reproduce it.

**Failure**

- Underlying records outside my permission are withheld from drill-down.
- If a filter is invalid, the report identifies the issue. If a selected total has no contributing records, drill-down shows an empty result for those filters.

Processes: [UC-43](#uc-43-compare-eb-performance-and-inspect-metric-sources).

##### 3.1.8.8 Export a performance summary (FR-ANL-08)

As the DoSA Head, I want to export a performance summary so I can review the selected reporting period and measures.

**Success**

- The export identifies the club or event, reporting period, extraction time, filters, measure definitions, and verification or coverage notes.

**Failure**

- Restricted records, private member fields, bill attachments, and their links are excluded unless permitted for that export.
- A failed export shows a failure rather than a completed file. An empty valid selection is identified with its chosen scope and reporting period.

Processes: [UC-44](#uc-44-export-scoped-performance-summaries).

##### 3.1.8.9 Recalculate using authorized corrections (FR-ANL-09)

As an authorized report reviewer, I want totals recalculated from accepted corrections so figures reflect the latest valid records.

**Success**

- The report uses current valid records and counts each linked correction once. Reviewers with access can inspect the correction history.

**Failure**

- Superseded data is not counted twice. Running a report cannot alter the underlying records or their versions.
- If recalculation fails, the system identifies the failure and leaves source records intact. An older report retains its original reporting time and scope.

Processes: [UC-43](#uc-43-compare-eb-performance-and-inspect-metric-sources).

#### Shared platform requirements

Apply search, notification, history and recovery rules wherever users encounter them. See processes UC-45 through UC-47.

##### Search records within granted access (FR-COM-01)

As an authorized user, I want search to return relevant records within my access so I can find clubs, memos, events, bookings, and financial entries.

**Success**

- The relevant screens support search and applicable club, date, and status filters. Selecting a result opens the original record after a new access check.
- A valid search with no accessible matches returns an empty result. The user can change the available filters.

**Failure**

- Records outside my current permissions do not appear, and an old link cannot bypass the access check.
- A bad filter or failed search is distinguished from a valid empty result. Restricted record counts and names are not disclosed.

Processes: [UC-45](#uc-45-search-and-filter-authorized-records).

##### Send notices and show delivery outcomes (FR-COM-02)

As a workflow participant, I want timely in-app notices and required IUB emails so I can follow changes and act on requests.

**Success**

- Notifications cover applicable submissions, decisions, requests for changes, deadlines, booking updates, and profile corrections. Each in-app notice records the event type, related record, recipient, time, and authorized link.
- Required emails go to IUB addresses. Memo rejection recipients follow FR-MEM-08, and profile request notices follow FR-IAM-05.

**Failure**

- Failed email delivery does not undo the business action. Authorized staff can inspect the failure and retry delivery.
- Retrying an email uses the original notification and intended IUB recipient. It does not repeat the underlying business action.

Processes: [UC-02](#uc-02-provision-accounts-and-control-assignments), [UC-03](#uc-03-view-profile-and-request-corrections), [UC-04](#uc-04-use-role-dashboard-and-follow-notifications), [UC-22](#uc-22-confirm-approve-or-reject-a-submitted-memo).

##### Record material actions (FR-COM-03)

As the DoSA Head, I want material actions logged so I can track how a record changed.

**Success**

- History records account and privilege changes, submissions, signatures, decisions, venue and fund confirmations, corrections, and publication actions.
- An entry identifies the actor, action, record ID, time, and relevant before and after references. Authorized staff can open it from the record.

**Failure**

- Audit entries cannot be edited by users. Unauthorized users cannot open restricted history.
- If a material action cannot save its required audit record, it remains uncommitted. The protected record history does not expose entries outside the viewer's scope.

Processes: [UC-46](#uc-46-inspect-material-action-and-version-history).

##### Save related changes together (FR-COM-04)

As an authorized user making a booking or financial update, I want its dependent records saved together so a partial update cannot create an inconsistent result.

**Success**

- A related action is saved as one logical update, such as booking confirmation and reservation or a financial correction and its source reference.
- A retried request for an already committed operation returns its recorded outcome where applicable.

**Failure**

- If saving fails, the application shows the failure and keeps the previous state. Retrying the same action safely leaves one official result.
- A simultaneous or interrupted operation cannot persist only one part of the update.

Processes: [UC-21](#uc-21-validate-and-send-a-memo-to-the-faculty-advisor), [UC-22](#uc-22-confirm-approve-or-reject-a-submitted-memo), [UC-31](#uc-31-review-and-confirm-a-venue-booking), [UC-32](#uc-32-reschedule-or-cancel-venue-booking), [UC-34](#uc-34-complete-or-cancel-an-event).

##### Keep versions and related records linked (FR-COM-05)

As a reviewer tracing a decision, I want saved versions and related records to keep their links so I can see what was approved.

**Success**

- Signatures, reviews, budgets, approved event details, notices, and financial evidence link to the exact versions they concern. Changed content follows the applicable approval process.
- Club-owned records retain their club ID. Term changes, archiving, or deactivating related profiles preserve earlier records and required links.

**Failure**

- A removal is blocked if it would leave a booking, bill, or decision without its source.
- A mismatched or superseded reference cannot silently attach approval, a signature, or evidence to the wrong version.

Processes: [UC-46](#uc-46-inspect-material-action-and-version-history).

##### Validate and protect file uploads (FR-COM-06)

As an authorized user, I want to upload and retrieve supporting files so evidence is accessible to the right people.

**Success**

- The application checks the type and size of an upload and links an accepted file to its record. Each download or preview rechecks permission.

**Failure**

- Disallowed files are rejected or quarantined, with the outcome shown in the form. The evidence remains unverified while requirements are unmet. Unauthorized retrieval is denied.
- Interrupted uploads can be retried without replacing accepted evidence. An expired or revoked file link is denied without exposing the document.

Processes: [UC-13](#uc-13-record-expense-and-attach-original-receipt).

##### Add historical records with their source (FR-COM-07)

As the DoSA Head, I want to add historical club and event records so verified and historical-only information can be found with its source.

**Success**

- During setup I can enter source, original author when known, import date, and verification status. Historical-only records retain their label.

**Failure**

- Duplicate identities or invalid references are rejected. Historical-only entries cannot create a live approval, booking, or finance decision without a new action meeting the applicable workflow.
- Missing required provenance or a failed import leaves out the unverified change. A retry cannot create another record for the same identifier.

Processes: [UC-47](#uc-47-import-verified-historical-clubevent-records).

##### Show errors and preserve recoverable drafts (FR-COM-08)

As a user editing a draft, I want helpful error messages and recoverable input so I can correct a failed save or submission.

**Success**

- After correcting the indicated issue or reloading the current version, I can resubmit my draft.

**Failure**

- If saving or submitting fails, the application identifies the affected field or rule, explains how I can resolve it, and preserves recoverable input where possible.
- If a newer draft exists, the application warns me and offers the current version to compare or reload before I resubmit.
- If the connection drops before success is confirmed, the interface does not show a completed submission until server state confirms it. A retry follows FR-COM-04.

Processes: [UC-19](#uc-19-draft-and-save-a-structured-memo).

### 3.2 Nonfunctional requirements

**NFR-SEC-01** Protected application pages and APIs shall require an active application session from verified IUB Google sign-in. Server-side checks shall enforce the active persona, grants, and club or term scope. The sign-in entry point remains available to provisioned users. Public registration, guest browsing, and unauthorized cross-club access are denied.

**Verification.** Check access before and after sign-in, sign-out, expiry, deactivation, and changes to role or club scope. Test protected records and direct links for each applicable role.

**NFR-SEC-02** The application shall use the verified IUB Google sign-in defined in FR-IAM-01. Credentials, identity-provider secrets, and API secrets shall be protected from exposure in code, logs, exports, or responses.

**Verification.** Credential and configuration audit; secret-scanning and log inspection.

**NFR-SEC-03** All browser-to-server and service-to-service traffic containing credentials or personal/financial information shall use encrypted transport; protected files shall require authorized retrieval.

**Verification.** TLS configuration and unauthorized-file-access test.

**NFR-SEC-04** Role grants, approvals, bill verification, fund-release confirmation, and administrative changes shall be audit logged with immutable business history.

**Verification.** Inspect audit records after representative successful and failed authorization scenarios.

**NFR-PRI-01** Private EB member information, memoranda, and financial evidence shall be available only to authorized account holders within the applicable club scope. Any optional external publishing integration shall receive only specifically approved event fields.

**Verification.** Inspect authenticated screens, API responses, exports, and any specifically approved external publication output.

**NFR-PRI-02** External AI/OCR providers, when enabled, shall receive only fields and files needed for the task under a configured data-handling arrangement; provider failure shall not erase originals.

**Verification.** Review adapter payloads and test unavailable-provider scenarios.

**NFR-PER-01** Under a documented pilot dataset of 50 clubs, 1,000 events, 5,000 memos, and 10,000 expense entries with 50 concurrent active users, 95% of ordinary page/API reads shall finish within 3 seconds, excluding bulk exports and AI/OCR processing.

**Verification.** Run repeatable load tests on an identified deployment environment and report p95 latency.

**NFR-PER-02** Venue conflict validation and a single final booking confirmation shall complete within 5 seconds at the same pilot load, and concurrent confirmations shall never yield overlapping confirmed slots.

**Verification.** Concurrent transaction/load tests with forced race conditions.

**NFR-REL-01** The production deployment target shall be at least 99.5% monthly availability excluding announced maintenance; no reliability promise is implied for a local development demonstration.

**Verification.** Service-monitoring report after deployment.

**NFR-REL-02** Backups shall include relational records, object-file references, and recoverable stored documents; a backup/restore runbook shall be tested before production use.

**Verification.** Restore a backup to a separate environment and verify sampled records and attachments.

**NFR-REL-03** Failures during submissions, status transitions, financial adjustments, or booking approvals shall preserve transactional consistency and support safe retries.

**Verification.** Fault-injection and duplicate-request tests.

**NFR-USE-01** Interfaces shall use consistent navigation, descriptive action labels, meaningful empty states, and status text in addition to color; users shall receive confirmation before irreversible actions.

**Verification.** Scenario-based usability review across all user roles.

**NFR-USE-02** Primary workflows shall be operable with keyboard navigation and assistive technology, targeting WCAG 2.2 Level AA for the university web interface.

**Verification.** Keyboard audit, automated accessibility checks, and manual screen-reader review.

**NFR-CMP-01** The system shall support current versions of major standards-compliant desktop browsers and responsive phone/tablet layouts without loss of core review information.

**Verification.** Cross-browser tests and responsive viewport checks.

**NFR-DAT-01** Event date-time values shall be stored unambiguously, presented in the Asia/Dhaka time zone, and checked across the full interval against confirmed reservations and configurable restricted hours; monetary amounts shall use fixed-precision decimal storage.

**Verification.** Boundary tests for dates, overnight events, decimal sums, and invalid state moves.

**NFR-DAT-02** Core records shall have stable identifiers, enforced references, and documented required fields; hard deletion of financially or administratively referenced history shall be restricted.

**Verification.** Schema integrity tests and archive/delete attempt tests.

**NFR-MNT-01** The implementation shall keep authorization, event/venue logic, financial calculations, and AI provider adapters testable as distinct responsibilities.

**Verification.** Code review plus automated unit/integration test evidence.

**NFR-MNT-02** Migrations, configuration defaults, role-permission mapping, deployment setup, and operational recovery shall be documented and reproducible.

**Verification.** Provision a clean environment from instructions and run migrations and smoke tests.

**NFR-AIG-01** All AI-generated suggestions and OCR-extracted fields shall be labelled as machine-produced or unverified until reviewed by a human.

**Verification.** UI/API inspection for scheduling, priority, OCR, and financial flags.

**NFR-AIG-02** AI output shall not automatically grant memo approvals, confirm reservations, mark funds as released, verify bills, or publish events. Final administrative decisions remain under DoSA control; automatic conflict and restricted-hour rules may reject ineligible requests.

**Verification.** Test adversarial or invalid model outputs and inspect the resulting state.

**NFR-AUD-01** Reports and exports shall identify the time, filters, revision basis, and inclusion of unverified data so that results can be reproduced.

**Verification.** Repeat exports with fixed filters and compare reconciled totals.

**NFR-LOC-01** The application shall use Asia/Dhaka as the default display time zone and BDT as the default currency display, while explicitly recording the currency of financial entries.

**Verification.** Locale test of midnight events, report totals, and mixed-currency inputs.

### 3.3 Shared business rules and financial definitions

**BR-01** Club-owned records retain their club identity. Cross-club access requires a separate authorized grant.

**BR-02** A signature or approval refers to an immutable version. Changed content requires the applicable new decision.

**BR-03** Memo handoff, DoSA queue entry, approval deadline, event start, and venue reservation time are separate fields.

**BR-04** Only a conflict-free confirmation with the booking route’s required approvals creates an exclusive reservation.

**BR-05** Allocated funds, scheduled releases, and confirmed releases are distinct figures.

**BR-06** Human-verified financial figures and OCR suggestions are kept separate.

**BR-07** Cancellation and archiving preserve historical decisions, bills, ledger entries, and links.

**BR-08** Material event changes trigger the applicable memo, booking, and publication checks.

**BR-09** AI and OCR output cannot directly change approval or financial state.

**BR-10** Repeated submissions, integration retries, or conflicting edits must not create duplicate official records.

**BR-11** Event cash flow includes explicitly attributed amounts. A general club allocation is not assumed to be event income.

**BR-12** Saved server state and version history determine the authoritative result when a screen or AI result is stale.

Allocated amount. Sum of valid allocation entries for the selected club and period; it is not proof of payment.

Released amount. Sum of recorded Released transactions minus linked confirmed reversals within the selected reporting scope; scheduled releases are excluded.

Verified expenditure. Sum of verified expense amounts and accepted adjustments, excluding rejected, returned, or unverified claims.

Recorded available balance. Confirmed recorded inflows for the same funding scope minus verified recorded outflows and adjustments. The display must state the scope and should not be described as a bank-certified account balance.

Event net cash flow. Confirmed inflows explicitly linked to the event minus verified event expenses, including linked corrections. Non-event allocations and incomplete amounts are displayed separately.

Reporting rule. All financial totals require a defined currency; multi-currency values must not be combined without an explicit conversion record and effective rate.

## Appendix A. Process catalogue

Use a process when building a complete interaction across screens or actors. The FR links identify the detailed validation and acceptance outcomes in Chapter 3. Priority follows the revised use cases.

### A.1 Club and Executive Body Management

#### UC-01 Sign in with IUB Google and end a session

**Actors.** Primary: System Admin, DoSA Head, EB member, or Faculty Advisor. Secondary: Google identity provider.

**Starts when.** A provisioned account holder opens the sign-in interface.

**Entry conditions.** The user has a provisioned active profile with an eligible IUB Google address.

**Main flow**

1. The user opens the sign-in page and selects IUB Google sign-in.
2. The user completes verification with Google. The application verifies the result on the server and matches the verified IUB address to one active profile.
3. The system establishes a session and opens the permitted dashboard. It checks current grants and assignments for each protected request.

**Alternate paths**

- The user signs out, or the session expires. To regain access, the user completes IUB Google sign-in again.

**Exceptions and recovery**

- A personal address, unprovisioned or inactive profile, or invalid result creates no session. The error does not disclose whether a profile exists.
- If sign-in is cancelled or Google is unavailable, the entry page remains available for a new attempt.
- Direct links fail after sign-out, deactivation, expiry, or revocation.

**Result.** A verified session exposes only permitted actions. A signed-out, expired, or revoked session cannot access protected resources.

**Trace.** [FR-IAM-01](#3111-sign-in-with-an-iub-google-account-fr-iam-01), [FR-IAM-02](#3112-assign-persona-scope-and-privileges-fr-iam-02), BR-01. Priority: High.

#### UC-02 Provision accounts and control assignments

**Actors.** Primary: System Admin or DoSA Head. Secondary: assigned Faculty Advisor for club onboarding.

**Starts when.** The system needs its first DoSA Head or an existing profile requires provisioning or an assignment change.

**Entry conditions.** The acting administrator is signed in and has the relevant account and grant privileges.

**Main flow**

1. A System Admin creates the first DoSA Head. After setup, authorized account administrators can maintain supported profiles.
2. For club onboarding, the Faculty Advisor emails the DoSA Head a spreadsheet with member details and requested access. The administrator reviews it and enters approved information in the application.
3. The administrator enters the IUB address and profile details, selects the access category, records the typed designation, and chooses named modules and actions. EB profiles link to a club and term. Advisors link to their assigned clubs. Assignments have start dates and end dates when known.
4. The system validates and saves the profile, assignment dates, and grants with the granting actor. A newly created profile receives sign-in instructions at its IUB address only.

5. Apply the single DoSA Head and shared EB role model. Record one officeholder per designation per active club term and allow a person to hold multiple designations.

**Alternate paths**

- An authorized administrator changes grants, deactivates a profile, or reactivates it after checking assignments. Ended assignments stop authorizing access while history and unrelated active grants remain available.
- The profile form records identity, contact, and academic details where applicable. Its Department and Major fields offer N/A when appropriate.

**Exceptions and recovery**

- Missing or invalid fields, duplicate IUB addresses, or incompatible grants or assignment dates block the affected change.
- An administrator cannot delegate beyond their grant. A typed designation alone grants no access.
- Failed invitation delivery can be inspected and retried without creating another profile.

**Result.** The profile, scope, and effective grants are saved with audit history. New users receive sign-in instructions at their IUB address.

**Trace.** [FR-IAM-02](#3112-assign-persona-scope-and-privileges-fr-iam-02), [FR-IAM-03](#3113-create-activate-and-deactivate-profiles-fr-iam-03), [FR-IAM-04](#3114-link-access-to-a-term-or-faculty-advisor-assignment-fr-iam-04), [FR-IAM-07](#3117-authorize-and-record-administrative-actions-fr-iam-07), [FR-COM-02](#send-notices-and-show-delivery-outcomes-fr-com-02), BR-01, BR-07. Priority: High.

#### UC-03 View profile and request corrections

**Actors.** Primary: any signed-in user. Secondary: active DoSA personnel for ordinary corrections, or an administrator authorized for protected fields.

**Starts when.** The user notices that a profile field needs correction.

**Entry conditions.** The requester has an active session and the selected field is eligible for a change request.

**Main flow**

1. The user opens Profile, selects the pen icon next to an eligible field, enters the proposed value, and submits.
2. The system validates the request, marks it Pending, and sends an in-app notice to active DoSA personnel. The saved value stays in effect.
3. An active DoSA reviewer decides an ordinary request. Changes to the sign-in address, role, club, tenure, or privileges route to an administrator with authority over that field.
4. The system records the decision and, if approved, applies the allowed change once. The requester can view the outcome in Profile.

**Alternate paths**

- The user may review their profile without requesting a change. A declined request leaves the saved value in effect.

**Exceptions and recovery**

- Invalid proposed values are flagged.
- A protected change cannot bypass account or assignment controls.
- If another reviewer already decided the request or the saved value changed during review, the system presents the current state before another change can apply.

**Result.** The requester can see the decision. An approved correction is applied once and records the old and new values, reviewer, and decision time.

**Trace.** [FR-IAM-05](#3115-view-profiles-and-request-changes-fr-iam-05), [FR-COM-02](#send-notices-and-show-delivery-outcomes-fr-com-02), BR-01. Priority: Medium.

#### UC-04 Use role dashboard and follow notifications

**Actors.** Primary: DoSA Head, System Admin, EB member, or Faculty Advisor. Modules and actions depend on current grants.

**Starts when.** A signed-in user needs to view current work.

**Entry conditions.** The user has an active session.

**Main flow**

1. The system presents the appropriate role-specific dashboard.
2. The user reviews pending work, record status, and update timestamps within their scope.
3. The user opens a linked task or notice.
4. The system applies record-level authorization before showing details.

**Alternate paths**

- The user may open a pending dashboard task directly instead of first opening a notification.
- The dashboard shows an empty state if no items are available. For required IUB email that failed, authorized staff inspect and retry the same notification.

**Exceptions and recovery**

- An unrelated club’s private tasks are hidden.
- A failed notification delivery does not undo the associated completed action.
- An inaccessible linked record is not disclosed.

**Result.** The user sees actionable and permitted work without cross-club disclosure.

**Trace.** [FR-IAM-06](#3116-open-a-role-dashboard-fr-iam-06), [FR-COM-02](#send-notices-and-show-delivery-outcomes-fr-com-02), BR-01, BR-12. Priority: Medium.

#### UC-05 Configure administrative workflow rules

**Actors.** Primary: DoSA Head with the administrative-settings privilege.

**Starts when.** DoSA needs to modify applicable system workflow settings.

**Entry conditions.** An authorized user is signed in and the applicable institutional rules are available.

**Main flow**

1. The authorized user opens workflow settings.
2. The user sets submission lead times, working-day calendars where applicable, venue restrictions, and permitted notification preferences.
3. The system validates the settings and records the editor, rule version, and effective date.
4. New submissions use the applicable rule version. Final booking confirmation uses the current venue rules for the interval.

**Alternate paths**

- An in-review memo retains the rules saved at submission unless an authorized restart is recorded. Future-dated rules become effective on their recorded date.

**Exceptions and recovery**

- Invalid settings or attempts to remove required stages or recipients are rejected.
- A failed save leaves the previously effective settings in place.

**Result.** A versioned policy configuration is saved without silently changing active submissions.

**Trace.** [FR-IAM-08](#3118-configure-administrative-settings-fr-iam-08), BR-02, BR-08. Priority: High.

#### UC-06 Maintain club register and internal club profile

**Actors.** Primary: DoSA Head with club-management privileges for official club details, or EB members with permission for their own club profile.

**Starts when.** A club record or permitted internal profile needs updating.

**Entry conditions.** The user is signed in; DoSA controls the institutional register and EBs have club-scoped profile permission.

**Main flow**

1. DoSA creates or updates a club identity/status, or an authorized EB edits internal club description fields.
2. The system validates the club-scoped changes.
3. The system saves the institutional or club-profile information.
4. Authorized viewers open the updated internal club page.
5. The system retains the club identifier across later EB terms.

**Alternate paths**

- DoSA maintains institutional club fields; an authorized EB member instead updates only permitted profile text for the assigned club.

**Exceptions and recovery**

- Only DoSA changes official club identity or status.
- Users cannot view another club’s private profile.
- Archiving prevents new work but retains historical records.
- An invalid internal contact or an attempt to edit another club’s profile is rejected.

**Result.** Club identity remains stable across terms and the relevant internal profile is updated.

**Trace.** [FR-CLB-01](#3119-maintain-the-official-club-register-fr-clb-01), [FR-CLB-07](#31115-maintain-the-internal-club-profile-fr-clb-07), BR-01, BR-07. Priority: High.

#### UC-07 Manage EB terms, appointments and handover

**Actors.** Primary: DoSA Head with EB term, membership, and handover privileges.

**Starts when.** An EB term starts, changes, or closes.

**Entry conditions.** DoSA is authenticated and the club exists.

**Main flow**

1. DoSA records term boundaries and its club.
2. DoSA appoints members to configurable posts with responsibilities and effective dates.
3. The system validates the changes and records the related audit details.
4. At handover, DoSA records outgoing/incoming terms and permitted unfinished work.
5. Old privileges end and incoming privileges begin according to assignments.
6. The system retains the outgoing members’ historical authorship and decisions after privileges end.

**Alternate paths**

- During handover, incoming members may finish specifically authorized pending work while original term attribution remains unchanged.

**Exceptions and recovery**

- Conflicting active terms are blocked unless an authorized transition is recorded.
- Duplicate or overlapping appointments are flagged.
- Historical actions remain with the originating term.
- An item that becomes ineligible before handover is saved cannot transfer as unfinished work.

**Result.** Term history and access transitions are recorded without losing prior work.

**Trace.** [FR-CLB-02](#31110-create-and-close-eb-terms-fr-clb-02), [FR-CLB-03](#31111-appoint-eb-members-and-record-positions-fr-clb-03), [FR-CLB-06](#31114-record-a-leadership-handover-fr-clb-06), BR-01, BR-07. Priority: High.

#### UC-08 View current organogram and legacy EB archive

**Actors.** Primary: DoSA Head, EB members, or Faculty Advisors with relevant club or archive access.

**Starts when.** An authorized person wants to inspect leadership history.

**Entry conditions.** The viewer has club-scoped read permission.

**Main flow**

1. The viewer selects an authorized club.
2. The system displays the current EB term organogram from recorded appointments.
3. The viewer selects a previous term or searches archived records.
4. The system displays only permitted historical membership, events, and achievements.
5. Term dates and current-versus-historical labels remain visible in the permitted view.

**Alternate paths**

- The viewer can select a previous EB term or search historical records instead of viewing only the current organogram.
- If no current term is recorded, the viewer can still open permitted historical terms.

**Exceptions and recovery**

- Missing older records are shown as unavailable, not invented.
- Archived historical corrections preserve previous values and editorial audit details.

**Result.** Leadership and tenure records are traceable across successive EBs.

**Trace.** [FR-CLB-04](#31112-view-the-club-organogram-fr-clb-04), [FR-CLB-05](#31113-browse-and-correct-the-eb-archive-fr-clb-05), BR-07. Priority: Medium.

### A.2 Financial and Fund Management

#### UC-09 Record allocations and fund release status

**Actors.** Primary: DoSA Head with fund-management privileges.

**Starts when.** DoSA needs to record allocation or funding activity.

**Entry conditions.** DoSA is authenticated; a club and funding period exist.

**Main flow**

1. DoSA records an allocation with currency, period, amount, and source.
2. DoSA may schedule a release separately from allocation.
3. When confirmation evidence exists, DoSA marks the release Released with amount/date/reference.
4. The system recalculates totals using valid released entries and adjustments.
5. The system leaves scheduled or cancelled release amounts outside the confirmed-released total.

**Alternate paths**

- DoSA may schedule a future release without marking funds as received; confirmed releases can later be adjusted through linked reversals.
- An authorized user may cancel a scheduled release with a reason. A cancelled release cannot become Released.

**Exceptions and recovery**

- Scheduled/Cancelled transactions are not counted as released.
- Amounts must be valid nonnegative values.
- Corrections and reversals are linked rather than overwriting confirmed entries.

**Result.** Auditable allocated, scheduled, and released figures remain distinct.

**Trace.** [FR-FIN-01](#3121-record-allocations-by-funding-period-fr-fin-01), [FR-FIN-02](#3122-schedule-and-confirm-fund-releases-fr-fin-02), [FR-FIN-13](#31213-apply-financial-corrections-consistently-fr-fin-13), BR-05, BR-06. Priority: High.

#### UC-10 Review club funding overview

**Actors.** Primary: DoSA Head or EB members with finance viewing access for their club.

**Starts when.** A permitted user needs to check club funding status.

**Entry conditions.** The viewer is authenticated with access to the club.

**Main flow**

1. The viewer selects the club and reporting scope.
2. The system retrieves allocations, scheduled releases, confirmed releases, and verified expenses.
3. The system computes the recorded balance using the defined scope and currency.
4. The viewer inspects the source record behind each displayed figure.
5. The screen identifies the calculation scope and does not describe its total as a bank-certified balance.

**Alternate paths**

- The viewer may filter a different reporting period or inspect the source behind a total.

**Exceptions and recovery**

- A scheduled release is never shown as received funds.
- Unverified expenses are identified separately.
- Values in different currencies are not summed without recorded conversion.
- A recorded zero, missing data, and no qualifying entries are shown distinctly.

**Result.** The funding screen shows a reproducible, scoped recorded balance rather than a certified bank balance.

**Trace.** [FR-FIN-03](#3123-view-club-funding-and-recorded-balance-fr-fin-03), BR-05, BR-11. Priority: High.

#### UC-11 Prepare and revise event budget

**Actors.** Primary: EB members with club and event budget privileges.

**Starts when.** An EB member is planning an event budget.

**Entry conditions.** An authorized EB user has an event and relevant memo or draft association.

**Main flow**

1. The EB member opens the event budget form.
2. The member enters line descriptions, quantities where relevant, and planned amounts.
3. The system links budget and memo to the event and saves a version.
4. A later modification produces a new version showing changed line items.
5. The previous budget version remains available for review.

6. The EB enters the requested amount. The Advisor records endorsement or returns it for correction before further processing.

**Alternate paths**

- After an initial budget is saved, a further edit is stored as a new budget version rather than replacing an earlier version.

**Exceptions and recovery**

- Invalid amounts or a mismatched club/event link block saving.
- Earlier versions remain available for review.

**Result.** A versioned event budget is available for DoSA review.

**Trace.** [FR-FIN-04](#3124-prepare-and-revise-an-event-budget-fr-fin-04), BR-02. Priority: High.

#### UC-12 Review budget against verified expenditure

**Actors.** Primary: DoSA Head with the relevant finance review privilege.

**Starts when.** DoSA needs to compare planned and recorded event spending.

**Entry conditions.** The event has a recorded budget and expense records or an empty expense list.

**Main flow**

1. DoSA opens the event budget review.
2. The system retrieves the relevant budget version and verified expense totals.
3. The system displays planned cost, verified expense, and variance.
4. DoSA follows the underlying records where needed.
5. The screen flags a variance without performing any financial approval or disciplinary decision.

**Alternate paths**

- When no expense is verified, the review shows the recorded budget with verified-spending totals defined by the available records.

**Exceptions and recovery**

- Unverified expense claims do not silently become verified expenditure.
- An over-budget flag is advisory and does not make a disciplinary or approval decision.
- A missing applicable budget is identified. The comparison does not treat it as a zero budget.

**Result.** DoSA receives an evidence-based event budget comparison.

**Trace.** [FR-FIN-05](#3125-compare-planned-and-verified-event-spending-fr-fin-05), BR-06, BR-11. Priority: Medium.

#### UC-13 Record expense and attach original receipt

**Actors.** Primary: EB members with expense-entry privileges for their club.

**Starts when.** A financial-responsibility EB member needs to submit an expense.

**Entry conditions.** The user is authorized for the club and has a valid expense category or event.

**Main flow**

1. The user enters purpose, date, amount, currency, and event or general-expense attribution.
2. The user uploads a receipt image/PDF.
3. The system checks file type/size, club-event link, and expense fields.
4. The system stores the original document privately and links it to the expense.
5. The system leaves the submitted expense unverified until DoSA performs the required review.

6. When evidence is missing, save an awaiting-evidence record and notify the EB with a due date. The submitted evidence path resumes after upload.

**Alternate paths**

- The expense may be attributed to a permitted general club category rather than an event.

**Exceptions and recovery**

- Disallowed/oversized evidence is rejected or quarantined.
- Invalid negative amount or cross-club event link is rejected.
- A failed upload does not produce a verified bill.
- If an upload required as evidence fails, submission cannot advance. Retrying the submission cannot create another expense.

**Result.** The expense record and protected original evidence remain associated with the club.

**Trace.** [FR-FIN-06](#3126-create-and-submit-an-expense-fr-fin-06), [FR-FIN-07](#3127-attach-and-inspect-original-bills-fr-fin-07), [FR-COM-06](#validate-and-protect-file-uploads-fr-com-06), BR-01, BR-06. Priority: High.

#### UC-14 Run OCR and review potential duplicate flags

**Actors.** Primary: EB members with the relevant expense access, and DoSA Head with the finance review privilege.

**Starts when.** An authorized user requests extraction for a submitted receipt.

**Entry conditions.** A permitted original bill document exists.

**Main flow**

1. The system processes the bill through the configured OCR capability.
2. The system presents suggested vendor/date/amount/items alongside the original, marked Unverified.
3. A permitted user corrects or confirms suggested fields.
4. Possible duplicate or inconsistent evidence is flagged for DoSA inspection.
5. The interface keeps suggested data separate from DoSA-verified expense values.

**Alternate paths**

- If OCR is unavailable, authorized users can enter or correct bill data manually and leave the original receipt available.
- If OCR extracts only some fields, a permitted user checks the original and completes the missing details manually.

**Exceptions and recovery**

- Unreadable documents receive an extraction-failure status while originals remain.
- OCR absence does not block manual transcription.
- A duplicate flag is not a fraud verdict or automatic expense rejection.

**Result.** OCR suggestions and review flags are separately recorded from verified expenses.

**Trace.** [FR-FIN-08](#3128-extract-receipt-details-with-ocr-fr-fin-08), [FR-FIN-09](#3129-flag-possible-duplicate-or-inconsistent-bills-fr-fin-09), BR-06, BR-09. Priority: Medium.

#### UC-15 Verify, return, reject or correct expense

**Actors.** Primary: DoSA finance reviewer. Secondary: authorized EB submitter for returned expenses.

**Starts when.** An expense awaits DoSA verification or requires permitted correction.

**Entry conditions.** An expense with source evidence exists; only DoSA performs verification decisions.

**Main flow**

1. DoSA opens the submitted expense and its evidence.
2. DoSA verifies, returns, or rejects with the required reason and audit stamp.
3. If returned, an authorized submitter prepares a new revision.
4. A verified expense requiring later correction is changed only through a linked adjustment/reversal.
5. The system retains the original verified amount and links any later reversal to that source.

6. For a refund or unused release, the EB documents the amount and the Advisor reviews its reconciliation before a linked official adjustment is posted.

**Alternate paths**

- DoSA can verify, return, or reject the submitted claim; a returned record follows a new draft revision, while a verified amount changes by linked adjustment.

**Exceptions and recovery**

- Submitted/verified records are not overwritten in place in violation of their status.
- Reject/return reason is required.
- AI suggestions do not mark expenses Verified.
- Only one valid decision is recorded for the original state. A reviewer working on a stale revision is shown the current record.

**Result.** Official review outcomes and corrections preserve previous values and actor history.

**Trace.** [FR-FIN-10](#31210-verify-return-or-reject-an-expense-fr-fin-10), [FR-FIN-13](#31213-apply-financial-corrections-consistently-fr-fin-13), BR-06, BR-07, BR-09. Priority: High.

#### UC-16 Inspect event cash-flow ledger and bills

**Actors.** Primary: DoSA Head with finance permissions for the event and its records.

**Starts when.** DoSA needs to audit an event’s money movement.

**Entry conditions.** The event exists and DoSA is authenticated.

**Main flow**

1. DoSA selects an event and opens its cash-flow view.
2. The system displays only explicitly event-attributed inflows, expenses, and adjustments.
3. DoSA opens supporting original receipt files and sees verified entries separately from unverified OCR.
4. The system displays the event net cash flow based on defined verified amounts.
5. The screen displays verification status and excludes non-attributed general allocations from event inflow.

**Alternate paths**

- DoSA may drill into an individual expense or original receipt rather than viewing only the aggregate cash-flow total.
- Authorized finance staff record an event inflow with a source, or link the attribution to an existing source entry. An existing attribution is counted once.

**Exceptions and recovery**

- General allocations are not treated as event income without event attribution.
- Missing records are shown as Not recorded.
- Restricted evidence is never served without authorization.

**Result.** DoSA can trace event cash flow from totals to original documents.

**Trace.** [FR-FIN-11](#31211-view-an-event-cash-flow-ledger-fr-fin-11), [FR-ANL-03](#3183-check-bills-and-ocr-from-the-event-workspace-fr-anl-03), BR-06, BR-11. Priority: Medium.

#### UC-17 Export scoped financial records

**Actors.** Primary: DoSA Head with permission to export financial information for the requested scope.

**Starts when.** DoSA requests an auditable financial export.

**Entry conditions.** DoSA is signed in and authorized for the selected information.

**Main flow**

1. DoSA chooses club, period, currency, and status filters.
2. The system applies the same scope and authorization checks used on screen.
3. The system generates the report with date, scope, currency, and unverified-data indicator.
4. DoSA retrieves the export.

**Alternate paths**

- DoSA may change filters and regenerate the report; any unverified inclusion remains explicitly declared.

**Exceptions and recovery**

- Invalid filters are rejected.
- Cross-scope private evidence is excluded.
- Different currencies are not silently combined.
- A failed export does not produce a completed report. A valid empty export identifies its filters and the absence of matching records.

**Result.** An identifiable and reproducible finance export is produced.

**Trace.** [FR-FIN-12](#31212-export-financial-records-fr-fin-12), BR-05, BR-06. Priority: Medium.

### A.3 Memo Management and Approval

#### UC-18 Create and version memo templates

**Actors.** Primary: DoSA Head .

**Starts when.** DoSA needs an official memo format.

**Entry conditions.** The acting user has access to the template administration workspace.

**Main flow**

1. The user creates or opens a memo template.
2. The user specifies its DoSA-assigned label, information boxes, required fields and attachments, and Faculty Advisor and DoSA Head e-signature areas.
3. The system validates the template and saves a version. Active templates are available to EB authors.
4. Later edits create a new version. Existing memos and drafts retain the original template version.

**Alternate paths**

- Deactivating a template removes it from new-draft choices. Earlier drafts still retain their recorded version.

**Exceptions and recovery**

- A template with incomplete required stage or signature areas cannot be activated.
- A user without the template privilege cannot save or activate changes.

**Result.** Active memo templates are version-controlled and auditable.

**Trace.** [FR-MEM-01](#3131-create-and-choose-memo-templates-fr-mem-01), BR-02. Priority: High.

#### UC-19 Draft and save a structured memo

**Actors.** Primary: authorized EB member Secondary: None.

**Starts when.** An EB member starts a memorandum for an event.

**Entry conditions.** The member has a permitted club/event and an active DoSA template.

**Main flow**

1. The author selects an active template and event.
2. The system displays the Event Permission template with manual entry fields, recipient hints and attachment slots.
3. The author types the memo header, To, Through, From, date, subject, event dates, time, purpose, proposed venue and any required references. The author previews the Office Memo before handoff.
4. The system saves a draft linked to its author, club, event, and template version.
5. The draft remains editable only by permitted users and is not treated as an official submission.

**Alternate paths**

- A rejected memo can be revised as a new editable Draft under UC-23. The frozen version stays read-only.

**Exceptions and recovery**

- Missing required fields are identified at later preflight, not invented.
- Unauthorized edits are denied.
- Conflicting edits do not silently overwrite a newer draft.
- A failed save does not enter review. Recoverable input and accepted attachments remain available. A stale editor is warned before overwriting a newer draft.

**Result.** A club-scoped Draft is saved with its template version and any available attachments. Drafts may be incomplete and remain editable during Authorship.

**Trace.** [FR-MEM-02](#3132-author-and-save-a-memo-draft-fr-mem-02), [FR-MEM-03](#3133-complete-the-memo-information-fr-mem-03), [FR-COM-08](#show-errors-and-preserve-recoverable-drafts-fr-com-08), BR-02, BR-10. Priority: High.

#### UC-20 Record a reviewer e-signature for a memo version

**Actors.** Primary: assigned Faculty Advisor, designated additional signer, or DoSA Head at the relevant step.

**Starts when.** An assigned reviewer opens the current version to endorse, confirm or approve it.

**Entry conditions.** The submitted version is current and frozen, the actor is authorized for the current stage, and earlier required steps are complete.

**Main flow**

1. The system displays the exact current submitted version and relevant signatory area.
2. The assigned Advisor signs and confirms, a named additional signer endorses when required, and the DoSA Head signs and approves at the final stage.
3. The system checks the current version, actor, stage, and signature. It records the signature with the accepted decision and updates the status under UC-22.

**Alternate paths**

- A revised or amended memo collects new signatures for the submitted version. Rejection follows UC-22 with a reason.

**Exceptions and recovery**

- Missing signatures, invalid assignments, superseded versions, or incomplete prerequisites block advancement.
- A failed save leaves the current stage and prior history intact.

**Result.** The signature is stored with the reviewer, stage, version, action, and time when confirmation or approval is recorded.

**Trace.** [FR-MEM-04](#3134-confirm-a-memo-with-an-e-signature-fr-mem-04), BR-02. Priority: High.

#### UC-21 Validate and send a memo to the Faculty Advisor

**Actors.** Primary: authorized EB member Secondary: None.

**Starts when.** The EB author selects Send to Faculty Advisor.

**Entry conditions.** The authorized EB author has a draft linked to the applicable event and template.

**Main flow**

1. The author chooses Send to Faculty Advisor. A proposed venue is sufficient.
2. The application checks required fields, attachments, applicable event and budget links, and effective lead time.
3. The system records the current version, author, and handoff time, marks the memo Pending Advisor Confirmation, and notifies the assigned Advisor.
4. The handoff, later DoSA queue entry, approval deadline, and event start remain separate fields.

**Alternate paths**

- The author may correct validation errors and try again. Advisory warnings allow handoff when mandatory checks pass.

**Exceptions and recovery**

- Missing required fields or an invalid required attachment or link keeps the draft at Authorship. A late submission is flagged for review.
- A failed save leaves the prior stage intact. A retry does not duplicate the handoff.
- Notification failure after commit is handled separately under UC-04.

**Result.** The submitted version is frozen as Pending Advisor Confirmation. The Advisor receives a notice and the handoff is timestamped.

**Trace.** [FR-MEM-05](#3135-validate-each-stage-before-sending-the-memo-forward-fr-mem-05), [FR-MEM-06](#3136-send-the-memo-and-record-submission-fr-mem-06), [FR-MEM-11](#31311-track-submission-deadline-and-event-dates-fr-mem-11), [FR-COM-04](#save-related-changes-together-fr-com-04), BR-02, BR-03, BR-10. Priority: High.

#### UC-22 Confirm, approve or reject a submitted memo

**Actors.** Primary: assigned Faculty Advisor and DoSA Head, each at their respective stage. Secondary: EB author and assigned EB participants.

**Starts when.** A submitted version enters the assigned Advisor’s or DoSA Head’s review queue.

**Entry conditions.** The memo is Pending Advisor Confirmation, Pending Additional Signatures or Pending DoSA Approval. The reviewer is authorized for the current stage and opens the current frozen version.

**Main flow**

1. The assigned Advisor opens the submitted version, signs it, and selects Confirm.
2. The system records the Advisor decision. Each assigned additional signer endorses the frozen version. After the last required endorsement, the system records DoSA queue entry and marks it Pending DoSA Approval.
3. The DoSA Head reviews that same version, signs it, and selects Approve.
4. The system records the final decision and marks the memo Approved.

**Alternate paths**

- At either review stage, the reviewer selects Cancel to open Reject Memo, enters a short reason, and explicitly confirms. The system records Rejected.
- Advisor rejection sends the EB author and assigned EB participants an in-app notice and IUB email. The DoSA Head sees it in tracking and receives no rejection email for this path.
- DoSA Head rejection sends the EB author, assigned EB participants, and Faculty Advisor an in-app notice and IUB email.

**Exceptions and recovery**

- Rejection requires a reason and explicit confirmation.
- An unauthorized, out-of-order, superseded, or already-decided action cannot advance or reject the memo.
- If two decisions compete at one stage, only the first valid committed decision applies. Failed email does not undo it.

**Result.** The memo has a recorded stage decision with actor, time, version, and reason if rejected. The recorded result identifies the next required signer, the next approval stage, or the final decision.

**Trace.** [FR-IAM-07](#3117-authorize-and-record-administrative-actions-fr-iam-07), [FR-MEM-04](#3134-confirm-a-memo-with-an-e-signature-fr-mem-04), [FR-MEM-06](#3136-send-the-memo-and-record-submission-fr-mem-06), [FR-MEM-07](#3137-route-the-memo-through-the-three-stages-fr-mem-07), [FR-MEM-08](#3138-approve-or-reject-a-memo-fr-mem-08), [FR-COM-02](#send-notices-and-show-delivery-outcomes-fr-com-02), [FR-COM-04](#save-related-changes-together-fr-com-04), BR-02, BR-09. Priority: High.

#### UC-23 Revise and resubmit a rejected memo

**Actors.** Primary: authorized EB member Secondary: None.

**Starts when.** The EB author opens a Rejected memo using View and chooses to revise it.

**Entry conditions.** The current eligible memo was rejected or returned by an assigned reviewer and the author has access to it.

**Main flow**

1. The author reads the rejection reason and starts a new editable Draft linked to the rejected version.
2. The author corrects the draft and sends it to the assigned Faculty Advisor using UC-21.
3. The new frozen version repeats Advisor Confirmation and DoSA Approval, with fresh signatures for approving decisions.

**Alternate paths**

- The author may save the revised draft and complete Authorship later.

**Exceptions and recovery**

- Earlier signatures cannot authorize revised content.
- A pending submitted version stays read-only.
- If validation fails, the revision stays editable and the rejection history is preserved.

**Result.** The revised version has its own handoff and review history. Earlier signatures, dates, and decisions are preserved.

**Trace.** [FR-MEM-09](#3139-edit-and-resubmit-a-rejected-memo-fr-mem-09), BR-02. Priority: High.

#### UC-24 Track memo status and review history

**Actors.** Primary: EB author or permitted memo participant, assigned Faculty Advisor, DoSA Head, or staff with appropriate memo access.

**Starts when.** A permitted user checks the progress of a memorandum.

**Entry conditions.** The user is authenticated and has memo-scoped read access.

**Main flow**

1. The user opens Memo Management and selects an accessible memo.
2. View shows label, current state, responsible actor, and permitted history. States include Draft, Pending Advisor Confirmation, Pending DoSA Approval, Rejected, Approved, and Withdrawn.
3. The viewer inspects distinct Advisor handoff, DoSA queue-entry, approval deadline, and event dates.
4. The DoSA Head can see rejection history, including Advisor rejections. Internal DoSA notes are visible only to users with the relevant privilege.

**Alternate paths**

- When no actions are pending, an empty state still provides permitted history. An authorized deadline or event-date change recalculates timing and preserves recorded handoffs.

**Exceptions and recovery**

- Missing or invalid deadlines are flagged.
- View refreshes stale status from the official record.
- History and private notes remain subject to current authorization.

**Result.** The user can trace the current workflow state and permitted history.

**Trace.** [FR-MEM-10](#31310-view-pending-work-and-memo-progress-fr-mem-10), [FR-MEM-11](#31311-track-submission-deadline-and-event-dates-fr-mem-11), BR-02, BR-12. Priority: Medium.

#### UC-25 Initiate an amendment to approved memo content

**Actors.** Primary: authorized EB author. Secondary: assigned Faculty Advisor and DoSA Head when the amendment enters review.

**Starts when.** Approved event/memo details require a material revision.

**Entry conditions.** A memo has a recorded Approved version.

**Main flow**

1. The author starts a material amendment from the approved memo.
2. The system opens a linked amendment Draft and displays approved and proposed details separately.
3. The amendment follows Authorship, Advisor Confirmation, and DoSA Approval with new signatures.
4. Revised dates, venue, budget, or notices take effect after the applicable memo, venue, and publication checks.

**Alternate paths**

- The approved version remains in use while the amendment is pending, rejected, withdrawn, or blocked by a booking check.

**Exceptions and recovery**

- Old approval cannot be reused as authorization for changed material fields.
- The proposal is not silently published or substituted for approved event details.

**Result.** A new reviewable amendment exists without erasing the prior approval.

**Trace.** [FR-MEM-12](#31312-request-an-amendment-after-approval-fr-mem-12), BR-02, BR-08. Priority: Medium.

#### UC-26 Withdraw an eligible memo or export a version

**Actors.** Primary: authorized EB member Secondary: None.

**Starts when.** The memo author withdraws a request or needs a document copy.

**Entry conditions.** The EB author is authorized for the selected memo. To withdraw it, the current version must be an eligible draft or pending memo.

**Main flow**

1. The user selects withdrawal or export.
2. For withdrawal, the author supplies a reason and confirms the action.
3. The system records Withdrawn while preserving versions and decisions.
4. For export, the system produces a copy labeled with version, status, signatures, and export date.

**Alternate paths**

- Export produces an identified document copy without changing state; withdrawal requires a valid state and explicit reason.

**Exceptions and recovery**

- An ineligible status is not withdrawn.
- Withdrawal never deletes the audit trail or previously signed versions.
- If withdrawal and a review decision compete, only the first valid committed transition applies. A failed export does not produce a completed file.

**Result.** The withdrawn state or correctly labeled memo export is available.

**Trace.** [FR-MEM-13](#31313-withdraw-a-request-or-export-a-memo-fr-mem-13), BR-07. Priority: Medium.

### A.4 Event and Venue Booking Management

#### UC-27 Create event and manage controlled event changes

**Actors.** Primary: EB organizer for the assigned club, or DoSA Head with permission to create and manage central events.

**Starts when.** An authorized organizer plans or edits an event.

**Entry conditions.** The organizer has a permitted club or DoSA event scope.

**Main flow**

1. The organizer creates an event with unique ID, owner, title, type, schedule and contact.
2. The system links later memo, budget, and booking records to the event.
3. The organizer edits a permitted draft or proposes approval-sensitive changes.
4. The system retains pending amendments separately from approved event details.

**Alternate paths**

- The organizer can edit an eligible Draft directly; after approval, material changes instead create pending amendments.

**Exceptions and recovery**

- Invalid date-times and organizer scopes are rejected.
- Approved venue/time/budget changes trigger dependent memo/booking review.
- Cancelled events remain historical.
- The end time must be later than the start time. A stale save does not replace a newer draft.

**Result.** A coherent event record retains approved and proposed versions separately.

**Trace.** [FR-EVT-01](#3141-create-an-event-record-fr-evt-01), [FR-EVT-02](#3142-change-event-details-fr-evt-02), BR-08. Priority: High.

#### UC-28 Administer venues, central events and restricted hours

**Actors.** Primary: DoSA Head with venue-management privileges.

**Starts when.** DoSA needs to configure booking availability.

**Entry conditions.** The authorized DoSA user is signed in.

**Main flow**

1. DoSA creates/edits venue capacity, facilities, operating restrictions, and active status.
2. DoSA records institutional events, closures, or restricted-hour periods.
3. The system saves effective restrictions and associates them with affected venue or all venues.
4. All availability checks use the configured current restrictions.
5. The system checks restricted or overnight intervals in full in subsequent searches and requests.

**Alternate paths**

- DoSA may mark a venue inactive, record a temporary closure, or set restricted hours for one venue or all venues.

**Exceptions and recovery**

- EB accounts cannot change official venue rules.
- Requests overlapping a restricted period are blocked.
- Overnight restrictions apply to the complete interval.
- A proposed closure that overlaps a confirmed booking is flagged for DoSA to resolve. A closure does not silently cancel a confirmed reservation.

**Result.** The official venue catalogue and blocking intervals are current and auditable.

**Trace.** [FR-EVT-03](#3143-maintain-the-venue-catalogue-fr-evt-03), [FR-EVT-11](#31411-add-central-activities-and-venue-blocks-fr-evt-11), [FR-EVT-13](#31413-apply-restricted-hours-in-dhaka-time-fr-evt-13), BR-04. Priority: High.

#### UC-29 Search venue availability

**Actors.** Primary: Organizers, Faculty Advisors, or DoSA Head with permitted venue-search access.

**Starts when.** A permitted user needs a venue/time slot.

**Entry conditions.** The venue catalogue and available event records are accessible.

**Main flow**

1. The user filters venue, date, capacity, and permitted use.
2. The system compares full time intervals against confirmed reservations, pending requests, closures, and restricted hours.
3. The system labels slots free, pending, confirmed, or unavailable.
4. The user compares alternatives in the authorized calendar.
5. The availability view presents an informational status rather than promising a confirmed reservation.

**Alternate paths**

- A user may compare another permitted venue or time slot; pending versus confirmed conflicts are labeled separately.
- The search may return an empty result. The user can change the filters and can view availability without seeing other clubs’ private details.

**Exceptions and recovery**

- Pending requests are not represented as reservations.
- Touching intervals are allowed when no buffer creates overlap.
- Unrecorded real-world changes cannot be inferred.

**Result.** The user sees a time-specific, status-aware availability view, not a reservation guarantee.

**Trace.** [FR-EVT-04](#3144-search-venue-availability-fr-evt-04), [FR-EVT-06](#3146-detect-overlapping-intervals-fr-evt-06), BR-04, BR-12. Priority: High.

#### UC-30 Submit a venue booking request

**Actors.** Primary: EB organizers authorized to submit bookings for their event and club.

**Starts when.** An EB organizer selects a candidate venue slot.

**Entry conditions.** The club event has an approved event-permission memo and the member has booking permission.

**Main flow**

1. The EB enters venue, date, inclusive start/exclusive end, setup/cleanup interval, and required justification.
2. The system checks venue status, time interval, capacity, closures, and configured restrictions.
3. The system shows possible conflicts and submission validation.
4. An eligible request is saved as Pending for DoSA decision.
5. The saved Pending request retains the original event, venue, and interval references.

6. Select the classroom or common large-venue form and apply the route, signatures and attendance threshold in §2.6.

**Alternate paths**

- The organizer may search alternative intervals. Material changes to an approved date or venue require the corresponding amendment before confirmation.

**Exceptions and recovery**

- Invalid interval, inactive venue, inadequate capacity, or restricted time is blocked with a reason.
- The request does not reserve the venue or imply memo approval.
- If a slot has become confirmed or restricted since it was selected, the live check blocks submission with a reason.

**Result.** A Pending booking request is linked to the event and its approved event-permission memo.

**Trace.** [FR-EVT-05](#3145-submit-a-venue-booking-request-fr-evt-05), [FR-EVT-06](#3146-detect-overlapping-intervals-fr-evt-06), BR-04, BR-10. Priority: High.

#### UC-31 Review and confirm a venue booking

**Actors.** Primary: DoSA Head with the booking-review privilege. Secondary: EB requester receiving the decision.

**Starts when.** A pending venue request is ready for a DoSA decision.

**Entry conditions.** DoSA is signed in; the required memo/Faculty Advisor steps are completed.

**Main flow**

1. DoSA opens the Pending booking request and its linked approvals.
2. The system rechecks current confirmed intervals, venue closures, restrictions, capacity, and buffers.
3. DoSA confirms the request, returns it for correction, or declines it as permitted.
4. For approval the system atomically saves a Confirmed reservation and its exclusive time interval.
5. The recorded outcome updates booking status separately from memo or event approval status.

6. On a full-day Friday/Saturday classroom request, record both the Head and Admin form approvals. Confirm all occupied days together or none.

**Alternate paths**

- DoSA may return or decline the request with reason rather than confirm; its interval then remains unreserved.
- A returned request retains its reason and history. The organizer can correct it and resubmit it after validation.

**Exceptions and recovery**

- If another confirmation wins a race, the request stays unconfirmed with a conflict notice.
- Incomplete memo approvals or an unavailable venue block confirmation.
- Return/decline records time and reason.
- If saving fails, neither a Confirmed status nor a partial reservation is retained. A retry rechecks live availability.

**Result.** At most one overlapping confirmation exists for the venue; the decision is auditable.

**Trace.** [FR-EVT-07](#3147-confirm-a-conflict-free-reservation-fr-evt-07), [FR-EVT-08](#3148-review-and-decide-a-booking-request-fr-evt-08), [FR-COM-04](#save-related-changes-together-fr-com-04), BR-04, BR-10. Priority: High.

#### UC-32 Reschedule or cancel venue booking

**Actors.** Primary: Authorized EB organizer. Secondary: authorized DoSA booking reviewer when approval is required.

**Starts when.** An organizer needs to change an existing reservation.

**Entry conditions.** The event and booking are accessible; a confirmed booking exists if being released.

**Main flow**

1. An authorized organizer starts a reschedule or cancellation request.
2. For rescheduling, the system creates a linked Pending request for the proposed slot.
3. If required approvals and current checks pass, the replacement is confirmed and the original interval is released in the same operation.
4. For cancellation, the authorized organizer supplies a reason. The system records it and releases the confirmed interval.
5. The system shows the current reservation and retains the request history.

**Alternate paths**

- A reschedule starts a linked new request; cancellation instead releases the reservation while preserving history.

**Exceptions and recovery**

- A proposed alternate slot does not take over the old reservation without confirmation.
- If new slot conflicts, the previous confirmation is not silently rewritten.
- Related calendar/publication changes follow authorized approvals.
- If a replacement cannot be confirmed or saved, the original reservation stays in effect.

**Result.** The reserved interval changes only through an approved transition, or is released on cancellation.

**Trace.** [FR-EVT-09](#3149-reschedule-or-cancel-a-booking-fr-evt-09), [FR-COM-04](#save-related-changes-together-fr-com-04), BR-07, BR-08. Priority: High.

#### UC-33 View event calendar and separate approval states

**Actors.** Primary: DoSA Head, EB members, or Faculty Advisors with calendar and record access.

**Starts when.** An authenticated user wants an event or booking status.

**Entry conditions.** The user has permitted calendar/event access.

**Main flow**

1. The user opens month, week, or event-list view.
2. The user filters by club, venue, date, and status.
3. The system displays event status, memo state, and venue request state separately.
4. The user opens an authorized event detail.

**Alternate paths**

- The calendar may be switched among month, week, and list views without changing official event or booking states.
- If no visible events match, the calendar shows an empty result and supports revised filters.

**Exceptions and recovery**

- Restricted drafts from other clubs are hidden.
- A pending venue request or memo is not labeled an approved event.
- Cancelled events are visibly historical.

**Result.** Current event/booking states are visible without collapsing different approval meanings.

**Trace.** [FR-EVT-10](#31410-show-the-internal-event-calendar-fr-evt-10), [FR-EVT-12](#31412-show-separate-event-memo-and-booking-statuses-fr-evt-12), BR-03, BR-12. Priority: High.

#### UC-34 Complete or cancel an event

**Actors.** Primary: Organizers with permission to complete or cancel the event.

**Starts when.** The organizer needs to close event work.

**Entry conditions.** The event exists and the user is authorized for the corresponding action.

**Main flow**

1. The organizer selects Complete or Cancel, and the system checks the event state.
2. Completion of an approved event records Completed and its outcome.
3. For an eligible cancellation, the organizer enters a reason and confirms. The system closes active booking requests, releases the reserved interval, and applies the configured internal calendar and notice changes.
4. The system preserves linked memo, budget, expense, receipt, and audit history.

**Alternate paths**

- A valid completed event may be marked Completed; an eligible event may instead be Cancelled with reservation release.

**Exceptions and recovery**

- Invalid final-state transitions do not modify records.
- External publication failures are displayed and retryable; they do not delete the event history.
- If the required internal changes cannot commit together, the prior event and booking states remain.

**Result.** The event reaches a valid Completed or Cancelled state with preserved evidence.

**Trace.** [FR-EVT-14](#31414-complete-or-cancel-an-event-fr-evt-14), [FR-COM-04](#save-related-changes-together-fr-com-04), BR-07, BR-08. Priority: High.

### A.5 AI-assisted Event Scheduling

#### UC-35 Request advisory AI scheduling recommendations

**Actors.** Primary: EB organizers with scheduling access for the relevant club.

**Starts when.** An EB organizer seeks feasible event time/venue suggestions.

**Entry conditions.** The organizer is authorized, and the relevant venue/calendar data is available.

**Main flow**

1. The organizer supplies event type, preferred range, duration, expected size, and setup requirements.
2. The system checks mandatory inputs and sends minimum necessary data to the advisory service.
3. The system presents labeled eligible options or an unavailability message.
4. A single selection copies all eligible days to a proposed slot or amendment. Lodging the room form requires an approved memo and a fresh availability check.
5. The system rechecks availability at submission and again before DoSA confirms any resulting booking.

**Alternate paths**

- If no feasible suggestion exists, the system reports unavailability and the user can continue manual venue search.

**Exceptions and recovery**

- Impossible dates or missing mandatory inputs generate explanations.
- AI timeout/invalid response falls back to manual venue search.
- A suggestion never reserves or confirms a venue.
- Private member and finance documents are excluded from recommendation data.
- A stale suggestion is screened again before submission and confirmation. Only the blocked venue interval is shared where another club’s reservation affects availability.

**Result.** An advisory candidate or manual fallback is available without changing an official booking state.

**Trace.** [FR-AIS-01](#3151-request-scheduling-suggestions-fr-ais-01), [FR-AIS-02](#3152-screen-suggestions-against-booking-rules-fr-ais-02), [FR-AIS-03](#3153-compare-suggested-venues-and-times-fr-ais-03), [FR-AIS-04](#3154-use-a-suggested-slot-in-a-request-fr-ais-04), [FR-AIS-05](#3155-limit-the-data-used-by-ai-assistance-fr-ais-05), [FR-AIS-06](#3156-continue-scheduling-when-ai-is-unavailable-fr-ais-06), BR-04, BR-09. Priority: Medium.

### A.6 AI-assisted Approval Prioritization

#### UC-36 Review and manually order approval priority queue

**Actors.** Primary: DoSA Head. Secondary: System Admin with queue-management access.

**Starts when.** DoSA needs to identify pending work requiring attention.

**Entry conditions.** The DoSA Head has access to the approval queue. Queue-management actions require the corresponding privilege.

**Main flow**

1. The system reads separate submission, approval-deadline, event-start, and preparation lead-time fields.
2. The queue ranks memos awaiting DoSA Head decisions and shows timing factors, reasons for priority, and the calculation time.
3. The DoSA Head or System Admin may filter or reorder actionable items. An override saves the actor, reason, prior order or score, and expiry or removal.
4. The system recalculates after timing, policy, or status changes.

5. Use event start as the second sort key after the approval deadline. Record any Admin priority override and its reason.

**Alternate paths**

- When AI ranking is unavailable or stale, the queue shows earliest-deadline-first order. It flags missing deadlines, labels an empty queue, and refreshes from current data when the service recovers.

**Exceptions and recovery**

- Missing/invalid deadlines are flagged rather than guessed.
- Past events and overdue deadlines have separate warnings.
- If AI prioritization fails, deterministic deadline ordering is available.
- Manual order never bypasses mandatory approval stages.
- Overdue approval deadlines and past event starts are shown separately. Missing data is not given a fabricated priority.
- An expired override or a resolved request stops affecting the active queue.

**Result.** A transparent, human-controlled review queue reflects current recorded deadlines.

**Trace.** [FR-AIP-01](#3161-use-separate-dates-for-priority-fr-aip-01), [FR-AIP-02](#3162-prioritize-actionable-requests-fr-aip-02), [FR-AIP-03](#3163-explain-the-displayed-priority-fr-aip-03), [FR-AIP-04](#3164-distinguish-overdue-and-insufficient-time-fr-aip-04), [FR-AIP-05](#3165-filter-and-adjust-queue-order-fr-aip-05), [FR-AIP-06](#3166-fall-back-to-deadline-ordering-fr-aip-06), BR-03, BR-09. Priority: Medium.

### A.7 Club Websites and Event Publishing

#### UC-37 Preview and publish approved internal event notice

**Actors.** Primary: EB organizer for their own club, DoSA Head or System Admin.

**Starts when.** An eligible event is ready for its club page.

**Entry conditions.** For an event notice, the required memo, event and venue prerequisites have cleared. For a general announcement, the publisher has permission for the selected audience.

**Main flow**

1. An authorized publisher opens the approved event version.
2. The system validates eligibility and shows a destination preview of allowed event fields.
3. The publisher confirms internal publication.
4. The approved notice appears only on authenticated and appropriately scoped club pages/calendar.
5. The internal calendar and authorized club page reference the same approved event version.

**Alternate paths**

- For an ordinary club announcement, the EB selects only its own page. The DoSA Head and Admin may publish a general announcement across all internal club pages.

- The publisher may preview the allowed fields and return without publishing; only the approved current version is eligible.

**Exceptions and recovery**

- Draft changes or an unconfirmed booking cannot be published as approved.
- Private memos, receipt files, budgets and personal contacts are excluded.
- Unauthenticated visitors cannot open internal pages.
- If the approval or applicable venue confirmation changes after preview, the publisher must review the current eligible version before publishing.

**Result.** The approved event notice or general announcement is visible to the authorized audience.

**Trace.** [FR-PUB-01](#3171-check-publication-eligibility-fr-pub-01), [FR-PUB-02](#3172-preview-the-event-notice-fr-pub-02), [FR-PUB-03](#3173-display-notices-on-authorized-internal-pages-fr-pub-03), [FR-PUB-05](#3175-use-a-single-approved-event-version-fr-pub-05), BR-08. Priority: High.

#### UC-38 Publish event to configured external website

**Actors.** Primary: Authorized EB or DoSA publisher for the approved external destination.

**Starts when.** An authorized publisher wants the approved event on a separate club site.

**Entry conditions.** A suitable external destination and credentials are configured, and the event is approved.

**Main flow**

1. The publisher selects an approved external destination.
2. The system sends only permitted publication fields from the approved version.
3. The integration records attempt, outcome, external reference, and last success time.
4. The publisher can retry a failed eligible operation.
5. The system never exposes internal TOWNHALL pages to anonymous visitors through external publication.

**Alternate paths**

- If synchronization fails, a permitted user may safely retry the same destination operation without creating a duplicate notice.

**Exceptions and recovery**

- An unconfigured destination is unavailable rather than assumed to work.
- Failed sync remains explicitly Failed, without claiming the site was updated.
- Retries avoid duplicate external notices.
- If an attempt times out with an uncertain result, retry uses the existing publication reference where available. Success requires confirmation.

**Result.** An external attempt is traceable; the private TOWNHALL platform remains authenticated.

**Trace.** [FR-PUB-04](#3174-publish-to-a-configured-external-website-fr-pub-04), [FR-PUB-07](#3177-inspect-and-retry-external-publication-fr-pub-07), BR-09. Priority: Low.

#### UC-39 Update or withdraw published event notice

**Actors.** Primary: Authorized EB or DoSA publisher for the affected notice.

**Starts when.** An approved amendment or cancellation affects a published notice.

**Entry conditions.** An authorized publisher and a previously published event exist.

**Main flow**

1. The system identifies approved changes or cancellation.
2. An authorized publisher reviews the revised notice and selects update or withdrawal.
3. Internal publication is updated from the authoritative approved version.
4. Configured external destinations are synchronized where supported, with history retained.
5. The system records failed external synchronization explicitly without undoing the internal approved record.

**Alternate paths**

- An approved reschedule results in an updated notice; cancellation results in withdrawal or a Cancelled display as configured.

**Exceptions and recovery**

- A pending amendment is not published.
- Unsuccessful external updates show a failure state and allow a safe retry.
- Cancellation does not erase event or financial records.
- A delayed request for an older version cannot replace a newer published notice.

**Result.** Published event information remains consistent with the last approved event version.

**Trace.** [FR-PUB-06](#3176-update-or-withdraw-a-published-notice-fr-pub-06), [FR-PUB-05](#3175-use-a-single-approved-event-version-fr-pub-05), [FR-PUB-07](#3177-inspect-and-retry-external-publication-fr-pub-07), BR-07, BR-08. Priority: Medium.

### A.8 Performance and Legacy Analytics

#### UC-40 Browse club event cards and open event workspace

**Actors.** Primary: DoSA Head with access to the club event workspace.

**Starts when.** DoSA wants to inspect a club’s historical or current events.

**Entry conditions.** DoSA is authenticated.

**Main flow**

1. DoSA selects a club.
2. The system shows filterable event cards by term, period, type, and status.
3. DoSA opens an event card.
4. The system displays linked memo, venue booking, cash-flow, participation, and attachments when recorded.
5. Missing linked information is shown as “Not recorded” rather than guessed.

**Alternate paths**

- DoSA may filter events by term, type, date, or status before opening an individual event card.

**Exceptions and recovery**

- Missing fields are shown as Not recorded.
- Card labels do not imply unapproved work is Completed.
- An empty valid result allows the user to change the filters. Links still require authorization when opened.

**Result.** A selected event’s records can be inspected from one workspace.

**Trace.** [FR-ANL-01](#3181-find-event-cards-by-club-fr-anl-01), [FR-ANL-02](#3182-open-the-event-workspace-fr-anl-02), BR-07. Priority: Medium.

#### UC-41 Inspect source receipts and OCR in event analytics

**Actors.** Primary: DoSA Head with permission to open the event and its evidence.

**Starts when.** DoSA opens the financial evidence tab on an event.

**Entry conditions.** The event has permitted source references, possibly including zero bill records.

**Main flow**

1. DoSA opens the event cash-flow evidence view.
2. The system lists recorded expense statuses, source bill links, and extracted fields if available.
3. DoSA opens an original image/PDF and compares it with corrected or unverified text.
4. The system displays whether a value is human-verified or merely suggested.
5. The system revalidates authorization when a bill image or PDF is retrieved.

**Alternate paths**

- DoSA may view the original receipt alongside the corrected human transcription or an explicitly unverified OCR suggestion.

**Exceptions and recovery**

- A missing receipt is shown with the EB warning and due date, or an overdue label after the deadline.
- An OCR suggestion cannot appear as verified without authorized confirmation.
- Protected source files require authorization on retrieval.
- If the original file is unavailable, the screen identifies that condition and retains permitted expense and review details.

**Result.** The reviewer can distinguish original evidence, verified transcription, and machine-produced suggestions.

**Trace.** [FR-ANL-03](#3183-check-bills-and-ocr-from-the-event-workspace-fr-anl-03), BR-06. Priority: Medium.

#### UC-42 Record event participation and achievements

**Actors.** Primary: Authorized EB organizer for the event or term.

**Starts when.** An EB member documents completed event outcomes.

**Entry conditions.** The member is authorized for the relevant event/term.

**Main flow**

1. The organizer selects the club event/term.
2. The organizer records attendance, its source, achievements, event reach and an outcome summary. The Advisor confirms the proposed successful-event flag.
3. The system associates entries with event and EB term and records verification/estimate status.
4. The member saves the record for permitted analytics use.

**Alternate paths**

- Where attendance data is incomplete, the author may enter an identified estimate rather than a fabricated exact count.

**Exceptions and recovery**

- An unverified estimate remains labeled.
- Missing attendance is not stored or reported as zero merely because no measurement exists.
- An invalid attendance measure or an unrelated event/term reference is flagged.

**Result.** Event participation and achievements have traceable attribution.

**Trace.** [FR-ANL-04](#3184-record-attendance-and-achievements-fr-anl-04), BR-07. Priority: Medium.

#### UC-43 Compare EB performance and inspect metric sources

**Actors.** Primary: DoSA Head with performance reporting access.

**Starts when.** DoSA wants a term-by-term, evidence-based performance view.

**Entry conditions.** Recorded events, terms, and metrics are available within selected reporting scope.

**Main flow**

1. DoSA chooses club, EB terms, dates and statuses.
2. The system calculates defined event counts, verified spending, releases, and variance using explicit scope.
3. The system displays comparisons with term date ranges and measures/rates distinguished.
4. DoSA drills into source events or financial entries.
5. The comparison excludes voided values and exposes metric definitions and correction history.

6. Report completed, Advisor-confirmed successful, national and international completed events for the selected EB tenure. Each count links to distinct event IDs.

**Alternate paths**

- DoSA may compare counts, rates, or term ranges and drill into the contributing records to evaluate unequal EB terms.

**Exceptions and recovery**

- Unequal term durations are not silently equated.
- Void/corrected amounts are not double-counted.
- Missing measures are labeled Not recorded, and historical corrections retain audit history.
- Rates without a valid denominator or enough data are shown as unavailable with the missing basis identified.

**Result.** Reproducible EB comparisons connect aggregate metrics to underlying records.

**Trace.** [FR-ANL-05](#3185-compare-eb-terms-fr-anl-05), [FR-ANL-06](#3186-define-reporting-measures-fr-anl-06), [FR-ANL-07](#3187-filter-trends-and-open-source-records-fr-anl-07), [FR-ANL-09](#3189-recalculate-using-authorized-corrections-fr-anl-09), BR-06, BR-07. Priority: Medium.

#### UC-44 Export scoped performance summaries

**Actors.** Primary: DoSA Head with permission to export the selected performance information.

**Starts when.** DoSA needs an auditable club or event performance report.

**Entry conditions.** DoSA is authorized to view the selected club/event scope.

**Main flow**

1. DoSA chooses a reporting period, club and other supported filters.
2. The system applies matching record-level permissions and metric definitions.
3. The system generates an export with extraction time, scope and caveats about verification.
4. DoSA downloads the report.

**Alternate paths**

- DoSA can choose a different period or verification filter and regenerate a properly labeled report.

**Exceptions and recovery**

- Restricted member/bill fields cannot leak through export.
- Historical corrections and unverified items are identified as defined by export scope.
- A failed export returns no completed file. An empty valid selection retains its chosen scope and period.

**Result.** A traceable analytics report is generated with consistent source definitions.

**Trace.** [FR-ANL-08](#3188-export-a-performance-summary-fr-anl-08), BR-06. Priority: Medium.

### A.9 Shared platform processes

#### UC-45 Search and filter authorized records

**Actors.** Primary: Signed-in users with search and read access to the relevant records.

**Starts when.** The user needs to locate a record.

**Entry conditions.** The account has an active permitted assignment.

**Main flow**

1. The user enters keywords or applies supported date, status, and club filters.
2. The system searches applicable clubs, memos, events, bookings or financial records.
3. The system removes records outside the user’s rights.
4. The user opens a result’s original record.

**Alternate paths**

- The actor may use keyword search or supported date/status/club filters before opening an accessible original record.

**Exceptions and recovery**

- Other clubs’ private records do not appear.
- An outdated link is not treated as permission to view a record.
- The screen distinguishes invalid filters or search failure from a valid empty result.

**Result.** Search returns only original records within the signed-in user’s scope.

**Trace.** [FR-COM-01](#search-records-within-granted-access-fr-com-01), BR-01. Priority: Medium.

#### UC-46 Inspect material action and version history

**Actors.** Primary: DoSA Head with audit access to the affected records.

**Starts when.** DoSA needs to audit decisions or changed records.

**Entry conditions.** The authorized DoSA user is authenticated and the target record exists.

**Main flow**

1. DoSA opens a record’s history or material-action view.
2. The system retrieves actor, action, object ID, time, and applicable prior/new version references.
3. DoSA follows linked memo approvals, financial adjustments, bookings, or publications.
4. The system preserves historical versions while current valid records remain authoritative.

**Alternate paths**

- DoSA may select a prior version or follow a correction link; historical data remains immutable.

**Exceptions and recovery**

- Ordinary users cannot edit audit entries.
- Missing or invalid references fail integrity checks rather than leaving orphaned approvals.
- A stale screen does not override the server-side version.
- A material action whose required audit entry cannot be saved stays uncommitted.

**Result.** Material actions can be traced without mutating prior evidence.

**Trace.** [FR-COM-03](#record-material-actions-fr-com-03), [FR-COM-05](#keep-versions-and-related-records-linked-fr-com-05), BR-02, BR-07, BR-12. Priority: High.

#### UC-47 Import verified historical club/event records

**Actors.** Primary: DoSA Head with the historical-import privilege.

**Starts when.** DoSA enters historical material during system setup.

**Entry conditions.** The authorized DoSA user is signed in and an identifiable source is available.

**Main flow**

1. DoSA selects a supported historical club/event record.
2. DoSA enters source, author, import date, and whether the information is verified or historical-only.
3. The system checks identifiers and referential consistency.
4. The system stores the historical record without opening an unauthorized live approval state.
5. Imported records cannot create retroactively approved live requests.

**Alternate paths**

- If the source is incomplete, DoSA may import an explicitly historical-only or unverified record rather than claiming verified completeness.

**Exceptions and recovery**

- Duplicate identifiers and broken links are rejected.
- Incomplete historical sources retain Unverified/historical-only labels.
- Import does not bypass the rules for new live requests.
- Missing required provenance prevents import. A retry cannot create another record for the same identifier.

**Result.** Historical records are searchable and labeled with their evidence status.

**Trace.** [FR-COM-07](#add-historical-records-with-their-source-fr-com-07), BR-07, BR-10. Priority: Medium.

## Appendix B. End-to-end acceptance

Run each scenario with synthetic records and the named roles. Check both what users see and what is committed. AC identifiers are stable across the SRS, the technical requirements and the test suite.

### AC-01 Digital memo and resubmission

An EB author opens an active template, sends an eligible memo to the assigned Advisor, and checks the frozen version. The Advisor confirms with an e-signature. The DoSA Head rejects with a reason and the required recipients receive an IUB email. The EB starts a linked revision. The Advisor and Head sign the new version. Both versions and their decisions remain traceable. The EB submits a proposed room before any booking exists. Repeat with a Department Head required: after Advisor confirmation the Head queue remains empty until that signer endorses.

### AC-02 Concurrent venue requests

Two EB organizers submit requests for overlapping times at the same venue. When an authorized DoSA user attempts to confirm a request, the system checks availability and confirms only a conflict-free interval. A second overlapping request remains unconfirmed with a clear conflict notice, even if confirmation requests reach the server at the same time. For a full-day Saturday classroom, the booking remains Pending after the first of the two required form approvals. At evening classroom confirmation, check both Advisor and Department Head permission.

### AC-03 Separate finance states

An authorized DoSA user records an allocation and a scheduled fund release for a club. Neither is reported as received funds until DoSA records the release as confirmed. A verified expense updates the recorded balance; unverified extracted receipt text does not. An EB request for BDT 25,000 can be endorsed by the Advisor without representing either an allocation or a release.

### AC-04 Bill OCR and correction

An authorized EB member uploads a receipt, checks extracted fields, corrects an amount, and submits the expense. The original document remains accessible to authorized users; an authorized DoSA user verifies the expense, and duplicate detection remains advisory. A missing shop receipt triggers a warning with a due date. Passing the due date marks it overdue. Uploading a valid receipt allows verification.

### AC-05 AI scheduling fallback

An EB organizer requests schedule suggestions and selects an available slot. Before accepting the request, the system automatically blocks overlaps with existing confirmations or restricted hours. If AI assistance is unavailable, manual search remains available; final confirmation still requires DoSA approval. Request two consecutive days and occupy day two before confirmation. Neither day may be reserved by that request.

### AC-06 Priority and deadline change

Two pending memos have different submission, approval-deadline, and event dates. The dashboard explains their priority independently of submission order; updating one deadline refreshes the priority and keeps the previous change traceable. Give two requests the same approval deadline. The earlier event ranks first unless an authorized recorded override applies.

### AC-07 Publish and reschedule

After the necessary approvals, an authorized EB publisher previews and publishes an event on an authenticated club page. A later time change undergoes the required review before the approved internal or external notice is updated. Any failed external synchronization is visible and retryable. Publish an ordinary EB announcement to its club, deny the same account an all-clubs audience, then verify the Admin and Head can publish to all internal pages.

### AC-08 Cancellation with preserved history

A confirmed and published event is cancelled. The venue interval becomes free, internal event calendar information is withdrawn or marked cancelled, while memos, expenses, bills, and audit records remain available to authorized users.

### AC-09 EB handover and legacy

An authorized DoSA user closes an EB term and activates its successor. Outgoing EB accounts lose the expired permissions, while incoming EB members may carry out permitted unfinished work. Historical events and performance remain attached to their original terms. Count two completed events and one cancellation in one tenure. If one completed event is international and Advisor-confirmed successful, show completed 2, successful 1 and international 1.

### AC-10 DoSA event review

An authorized DoSA user selects a club, reviews its event cards, and opens an event record containing approved activities, cash-flow entries, original receipt files, and clearly identified OCR suggestions. Summary totals reconcile with the reporting definitions.

### AC-11 Cross-club authorization

An EB member changes the club ID in a direct URL or API request. The system denies access to another club's private event, memo, bill, and financial export, without leaking record contents.

### AC-12 Corrections and auditability

A verified expense receives a valid adjustment; the original is preserved, event cash flow and club reports recompute without double-counting, and a reviewer can inspect the linked adjustment and actor history.

### AC-13 Memo template versioning

The DoSA Head creates an active memo template with required fields, attachments, and areas for Advisor and DoSA Head signatures. An EB author submits using that version. Staff revise or deactivate the template. The submitted memo retains its original template, and new drafts cannot select the deactivated template.

### AC-14 Restricted hours and AI slot validation

DoSA restricts bookings during a specified venue interval. An EB organizer attempts to request a conflicting event through the ordinary form and through an AI-suggested slot. Both requests are blocked with a clear time conflict notice. A slot outside the restricted period may proceed for DoSA review if no other booking conflicts exist. Test 349, 350 and above-capacity headcounts on the common venue form. Only 350 or more within actual capacity satisfies both size checks.

### AC-15 Account access and role dashboard

A System Admin provisions the DoSA Head. Authorized staff provision an EB member and Faculty Advisor. A provisioned user signs in through IUB Google and sees the appropriate modules. For live use, a personal Google account, inactive profile, and anonymous calendar request are denied. Demonstration identities are isolated from live authentication. An EB member and Advisor can only open records for active club assignments and granted actions.

### AC-16 Advisor rejection and conflicting decisions

The assigned Faculty Advisor rejects a submitted memo with a reason. The EB receives the notice and IUB email. The DoSA Head sees the rejection in tracking and receives no rejection email for it. A later attempt to confirm the rejected version is denied. A separate race between two final decisions produces one official outcome.

### AC-17 Permission and profile changes

An approved ordinary profile correction applies once and is audited. A role-change request must go through an authorized account administrator. When an EB assignment ends, a previously opened event, receipt, or export link is denied if no other grant permits it. Historic work stays attributed to its original author and term.

### AC-18 Interrupted actions and retries

Interrupt a venue confirmation, finance correction, or memo handoff before commit and verify the prior state remains. Retry after commit and confirm one official result. Separately fail an IUB email or external sync after a saved business action and verify that status can be inspected and retried.

### AC-19 Boundary dates, stale slots and empty results

Check equal, contained, and adjacent venue intervals with and without buffers, including an overnight restriction. Change availability after a suggestion or search result appears and verify current validation blocks the conflict. A valid search with no matches produces a labelled empty result. Test an exactly seven-day workshop submission and a six-day submission. Only the latter receives the late warning. Test the calendar-month boundary for a Big event.

### AC-20 Financial evidence and mixed currencies

Upload a rejected file type, then a valid receipt with partial OCR, and complete the missing values manually. Compare a scheduled release, a confirmed amount, and a verified expense with an adjustment. Verify a missing conversion record keeps currencies separate and the adjustment is counted once.

## Appendix C. Delivery sequence and policy decisions

### C.1 Implementation increments

Build these increments in dependency order. Each ends with a demonstrable user journey. Feature and process identifiers continue to apply across increments.

1. **Access and club setup.** Provision a Head, create two clubs, appoint their members and verify sign-in, grants, ordinary profile corrections and direct-link denial. Demonstrate AC-15 and AC-17.
2. **First event and memo.** Create an event and draft budget, configure a template, submit, sign, reject and resubmit. Build version history, audit and the IUB notification outbox alongside this workflow. Demonstrate AC-01, AC-13 and AC-16.
3. **Booking and event lifecycle.** Configure a venue and restrictions. Demonstrate competing requests, final confirmation, atomic rescheduling, cancellation and the internal calendar. Run the database race in AC-02 and the boundaries in AC-19.
4. **Finance and evidence.** Record an allocation and release, submit an expense with an original receipt, verify it, apply a correction, and export reconciled totals. Add optional OCR behind the same manual review. Demonstrate AC-03, AC-04, AC-12 and AC-20.
5. **Publishing and assistance.** Publish an eligible version internally, exercise the external adapter, add explainable slot suggestions and queue priority with fallbacks. Demonstrate AC-05, AC-06, AC-07 and AC-14 with provider success and outage.
6. **Legacy, reporting and release.** Close a term and hand over unfinished work, import historical records, compare term measures and drill down to source bills. Demonstrate AC-08 through AC-11 and AC-18. Run all twenty acceptance scenarios and the technical quality checks before declaring full scope complete.

### C.2 Decisions required for live operation

- **DoSA Head and Faculty Advisors.** Confirm the prototype’s event-permission template, signing method, role assignments, budget prerequisites, withdrawal stages and amendment-sensitive fields. Capture the effective version and a representative approved example.
- **DoSA venue administrator.** Supply venue hours, local closures and overnight restrictions, setup/teardown buffers, capacity, permitted uses, and working-day rules. Verify a boundary example together before opening bookings.
- **DoSA finance reviewer.** Confirm mandatory evidence, budget variance conventions, reporting periods, currency precision and any allowed conversion evidence. Record the decision alongside a reconciled sample.
- **IUB identity and operations owners.** Supply eligible hosted domains, Google client registration, approved sender, storage and backup arrangements, retention policy and recovery objectives. Test with authorized accounts and a restoration rehearsal.
- **Club publisher and IUB data owner.** Approve destination credentials, field allowlists, permitted AI/OCR payloads and handling terms. Demonstrate recovery from a timed-out external write before enabling that destination.

### C.3 Definition of product acceptance

Record the build revision, policy versions, test data, role, expected result, actual result and evidence for each AC and each applicable FR outcome. A financial pass includes the calculation and its source rows. A workflow pass includes the actor, affected version, transition and notification recipients. A booking pass includes a race against a second database connection. Record unavailable production integrations as pending live verification even when their contract tests pass.

Start in Cursor with one executable slice. For example, use UC-02 and FR-IAM-03 to implement first-Head provisioning. First show a failing test for a duplicate institutional address. Then implement the smallest permitted provisioning path, verify the audit row and single IUB invitation, and run the suite. Proceed to sign-in and scoped access once this slice passes.


## Appendix D. Event-permission memo specimen

This English A4 example shows how the reference image translates to an event-permission memo. The source image is a support request: its To line is the Director, Operations & Maintenance, Through is the Head of DoSA, and From names a Faculty Advisor. For this Programming Club event, the EB types the intended recipient and routes Through the Advisor with their designation. The project owner’s required signatures appear underneath. The names, dates and recipient wording below are illustrative.

### Printable example

Independent University, Bangladesh (IUB)

[School name, if applicable]  
[Department name, if applicable]

**Office Memo**

**To**     Head, Division of Student Activities  
**Through**     [Advisor name], Faculty Advisor, IUB Programming Club  
**From**     [EB member name], President, IUB Programming Club  
**Date**     1 December 2026  
**Subject**     Request for permission to hold a programming workshop

The IUB Programming Club requests permission to hold a programming workshop on Friday, 18 December 2026, from 6:00 p.m. to 9:00 p.m. We propose to use [department classroom] for 40 participants. The workshop will give new members practice solving programming problems in teams.

Please contact [club contact] for enquiries. We request approval for the event and will submit the classroom booking form after event permission is granted.

**Faculty Advisor**     [e-signature, name, designation, signing date]  
**Department Head**     [e-signature for the evening classroom, designation, signing date]  
**Head, DoSA**     [final event e-signature, designation, signing date]

### Rendering and acceptance

Center the approved institution mark, institution, optional school and department, then the italic Office Memo title. Use a horizontal rule above the aligned To, Through, From, Date and bold Subject rows. Follow the second rule with the typed body, optional contact, closing and signature blocks. Omit unused affiliation rows. Use a text-only heading until an approved logo is available. Keep signature labels with their signature when a document spans pages. A draft is clearly labelled Draft in preview.

The synthetic 40-person example uses a classroom. It cannot be transferred unchanged to MPH, DMK or the Auditorium. For a large-venue proposal the EB must first check the minimum headcount and available capacity, then obtain approval for the appropriate event version.

### Prototype assumptions to confirm before live use

One persona means one role workspace and one active incumbent per named office in the pilot, with individual sign-in. The supplied Gmail address is a test identity only. One month means a calendar month. The Friday/Saturday full-day form requires both DoSA and Admin; the common large-venue form routes to DoSA with departmental endorsement when required. Two-day suggestions default to consecutive days at one venue. A successful event uses Advisor confirmation of the EB outcome report. The date of the course submission and individual team assignments remain unspecified and do not affect these product rules.
