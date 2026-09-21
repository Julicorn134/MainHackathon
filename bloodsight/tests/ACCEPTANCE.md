# Acceptance checks (written before the three sides were built)

Every check is an outcome claim: it counts only when observed in a real browser against a fresh
state file, by someone who did not build the screen. "Looks right" is not on this list: the look
is judged by a person.

Accounts: centre / centre123, lab / lab123, patient / patient123 (Alex, O-, donor part on),
patient2 / patient123 (Sam, A+, results only).

## Login
- L1 Wrong password is rejected and no role content is rendered.
- L2 Each of the three roles logs in with its username and password and lands on its own first page.
- L3 A patient never sees a centre or lab page, and the other way round (no page names of another role in the sidebar).
- L4 Sign-up with free lab code BL-4821 creates an account that can log out and log in again. A taken or unknown code is refused with a readable message.

## Blood centre
- C1 Outlook shows O- critical, shortage in 7 days, recommendation of 210 donations.
- C2 "Turn into a donor request" opens Requests with blood type O- and target 210 filled in.
- C3 The new-request form shows how many people match as a count, and the count changes with the distance.
- C4 Sending shows asked / seen / booked / not this time, and a bookings list. No name appears for anyone who has not booked.
- C5 After patient Alex books, the centre sees "Alex J." in bookings and gets a notification.
- C6 After Alex presses "Not this time" on a request, no screen of the centre shows Alex's name for that request.
- C7 A draft can be saved and sent later; a sent request can be closed; a closed request disappears from the patient's Needs.

## Lab
- B1 Publish results shows 212 reports, 205 ready, 3 code mismatches, 4 urgent values.
- B2 An urgent report cannot be released before "doctor has phoned" is recorded.
- B3 Before publishing, Alex's newest report is 3 Jun. After publishing it is 14 Sep and Alex has a "results ready" notification.
- B4 The lab can write a notification to all patients, to donors only, or to one patient; the count of recipients is shown; the message appears in that patient's inbox.
- B5 The lab's pages show no blood-centre request data and pass nothing but the blood type to the donor side.

## Patient
- P1 Results lists out-of-range values first, with the lab's own range, and folds the in-range rest.
- P2 Opening ferritin shows 18 ng/mL, range 30 to 300, the three-test trend (41, 33, 18) and an explanation marked as written by the AI that gives no diagnosis and no cause.
- P3 Needs shows a card only when there is a matching open request, and every card says why this person sees it.
- P4 Booking a slot takes at most two clicks from the card, shows up under Donations, and creates a notification.
- P5 Sam (patient2, donor part off) sees no needs. Switching "nearby" on under Me makes matching needs appear; "Pause all requests" empties the list again.
- P6 Ask answers from the person's own data, names its sources, and refuses a diagnosis, a cause, and a promise that the person can give blood.
- P7 The unread count in the sidebar goes up when a notification arrives and down to zero after "Mark all as read".

## Whole loop
- W1 centre sends O- request -> Alex sees need + notification -> Alex books -> centre sees the named booking and the booked count goes up by one.
