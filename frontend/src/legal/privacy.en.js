// The Privacy Policy, in English (privacy.fr.js is the French text; both must keep the same sections).
// A DRAFT for a lawyer to review before launch: the page says so while the server's LEGAL_DRAFT_NOTICE is on.
// {placeholders} are filled in from the server (/api/site/), so the policy states the real settings:
// entity, address, email, hosting, version, graceDays, santaDays, auditDays, usageDays, contactDays,
// backupDays, tempDays, sessionDays. [text](/path) is a link to a page of the app.
// When the meaning changes, raise LEGAL_VERSION on the server: everyone is asked to accept the new text.
export default {
  title: "Privacy Policy",
  intro: [
    "Iga is a learning app for secondary school students in Rwanda (Senior 1 to Senior 6), their teachers, their parents and their schools. Many of the people who use it are children.",
    "This policy explains in plain words what personal data Iga collects, why, where it is kept, who can see it, how long it is kept, and the rights you have under Rwanda's Law N° 058/2021 of 13/10/2021 relating to the protection of personal data and privacy. If something is not clear, ask us.",
  ],
  sections: [
    {
      id: "controller",
      title: "Who is responsible",
      body: [
        "{entity} ({address}) runs Iga and is the data controller: we decide why and how your personal data is used. Your school decides some things too, for example which teachers run your classes.",
        "For anything about your personal data, write to {email} or use the [contact page](/contact).",
      ],
    },
    {
      id: "data",
      title: "What we collect",
      body: [
        "We only collect what Iga needs to work.",
        {
          list: [
            "Your account: username, first and last name, password (kept only as a secure hash that nobody can read), role (student, teacher, parent or school administrator), grade and combination for students, preferred language, the avatar you build, and your email address if you give one. An email address is optional, except for school administrators.",
            "Your school: the school you choose and whether it has approved you. For a school: its name, district, sector, phone number and email address.",
            "Your learning: lessons completed, labs opened, quiz and exam attempts with your answers and scores, marks and feedback from teachers, the classes you joined, XP, streaks and badges.",
            "Study groups: the groups you join, your messages and shared notes, and the reports you make about messages.",
            "Questions to Santa, Iga's AI tutor: what you ask, what Santa answers, the lesson or subject, and how many questions you ask each day. Santa runs on Iga's own server: your questions are never sent to an outside AI company.",
            "The code playground: how many programs you run each day and how long they take. Your code itself is not kept.",
            "Payments, for school administrators: the subscription chosen, the amount, the currency, the date and whether it was paid. Card and mobile money payments are handled by Flutterwave. We keep the payment reference and the details Flutterwave sends back (they can include the payer's phone number, email address and the last digits of a card), encrypted. We never see or keep full card numbers or PINs.",
            "Messages you send us with the contact form: your name, email address, school and message.",
            "Security records: when you sign in, failed sign-ins, changes to your password or email, and the internet (IP) address a request came from.",
          ],
        },
        "We do not collect your date of birth, home address, photos or location, and Iga never uses your camera or microphone. We do not use advertising or tracking cookies, and we do not sell personal data.",
      ],
    },
    {
      id: "purposes",
      title: "Why we use it",
      body: [
        {
          list: [
            "To run your account and show you your lessons, labs, quizzes and progress: this is needed for the service you, or your school, asked for.",
            "So that teachers can teach: set work, mark answers and follow their classes' progress.",
            "So that the parents and guardians you link to can follow your progress.",
            "So that schools can manage their members and pay their subscription.",
            "To keep Iga safe: stop people guessing passwords, find misuse, and review reported messages and Santa's conversations to protect children.",
            "To send the emails you need: password reset links, notices about deleting your account and, for school administrators, receipts and subscription reminders.",
            "To meet our legal obligations, for example keeping payment records for tax purposes.",
            "To improve Iga with counts that name nobody, for example how many lessons were completed.",
          ],
        },
        "No important decision about you is made by a machine alone: quizzes are marked automatically from the correct answers, and your teacher can review them.",
      ],
    },
    {
      id: "children",
      title: "Children and parental consent",
      body: [
        "Most students on Iga are children. Under Rwandan law, the personal data of a child under 16 may only be processed with the consent of a parent or legal guardian.",
        {
          list: [
            "When a student under 16 creates an account, a parent or guardian must read this policy and the [Terms of Use](/terms) with them and agree. The sign-up form asks the student to confirm this.",
            "When a teacher creates accounts for a class, the school confirms that it has the consent of the parents or guardians, as for its other activities. The student also accepts these texts at their first sign-in.",
            "A parent or guardian can follow their child's progress by linking their own account with a code from the child's profile. They see progress only, never messages.",
            "A parent or guardian can ask us at any time to see, correct or delete their child's data, or withdraw their consent, by writing to {email}.",
          ],
        },
        "To protect children, Iga has no private messages: only group chats that can be reported and moderated. Other students only see your first name, the first letter of your last name, your avatar and your XP. Santa never sees other students' data.",
      ],
    },
    {
      id: "sharing",
      title: "Who can see your data",
      body: [
        {
          list: [
            "Your teachers, for the students in their current classes: name, username, grade, and work in the class subject or on the teacher's assignments.",
            "Your school's administrators: their members' names, usernames, roles, grades and membership status.",
            "Parents and guardians you link to: your progress, read-only.",
            "Other students: your first name and initial, avatar and XP on leaderboards and in groups, and the messages you post in your groups.",
            "The Iga team: only what is needed for support, moderation, child protection (reported messages and Santa's conversations) and to keep Iga running. Each look at the list of users is recorded.",
            "Companies that work for us under contract: the hosting provider of our servers, our email provider for the emails above, and Flutterwave for payments. They may only use the data to provide their service to us.",
            "Public authorities, when Rwandan law requires it.",
          ],
        },
        "We do not sell or rent personal data, and we do not share it with advertisers.",
      ],
    },
    {
      id: "storage",
      title: "Where your data is kept",
      body: [
        "Iga's data is kept on servers in {hosting}. If it ever had to be kept outside Rwanda, we would only do so as the law allows, with the authorisation of the National Cyber Security Authority (NCSA) and with protection at least as strong as described here.",
        "Flutterwave processes payment details in its own systems, under its own privacy policy.",
      ],
    },
    {
      id: "retention",
      title: "How long we keep it",
      body: [
        {
          list: [
            "Your account and your learning: as long as your account exists. If you delete your account, it is erased {graceDays} later (see Your rights).",
            "Questions to Santa and its answers: {santaDays}.",
            "Security and activity records: {auditDays}.",
            "Daily counts of Santa and code playground use: {usageDays}.",
            "Messages sent with the contact form: {contactDays}.",
            "A temporary password from a teacher stops working after {tempDays}.",
            "Payment and accounting records: as long as Rwandan tax and accounting law requires. They are never deleted early, even when an account is deleted: the person who paid is then shown only as \"Deleted account\".",
            "Backups: copies of the database are kept for {backupDays} and then deleted, so deleted data can remain in a backup for up to {backupDays}.",
          ],
        },
      ],
    },
    {
      id: "rights",
      title: "Your rights",
      body: [
        "Under Law N° 058/2021 you have the right to:",
        {
          list: [
            "See your data: Profile, then Privacy, then \"Download my data\" gives you a file with everything Iga holds about you.",
            "Correct it: change your name, grade, language and email address in your profile. For class information, ask your teacher or school, or write to us.",
            "Delete it: Profile, then Privacy, then \"Delete my account\". Your account is erased {graceDays} later, and signing in before then cancels the deletion.",
            "Object to, or ask us to limit, how we use your data, and withdraw your consent: write to {email}. Without consent you may no longer be able to use Iga, but what was done before stays lawful.",
            "Take your data elsewhere: the download is a standard file (JSON) that other services can read.",
            "Complain to the National Cyber Security Authority (NCSA), Rwanda's data protection authority, if you think we have not respected your rights.",
          ],
        },
        "We answer requests as quickly as we can, and within 30 days. We may first ask you to confirm who you are. A parent or guardian can use these rights for a child under 16.",
      ],
    },
    {
      id: "security",
      title: "How we protect your data",
      body: [
        {
          list: [
            "Every connection to Iga is encrypted (HTTPS).",
            "Passwords are kept as Argon2id hashes: nobody, not even the Iga team, can read them.",
            "Two-factor authentication secrets, schools' phone numbers and payment details are encrypted in the database.",
            "You can turn on two-factor authentication, and log out on every device, from your profile.",
            "Everyone sees only what their role allows. Sensitive actions ask for the password again and are recorded.",
            "Sign-in attempts are limited, and repeated failures lock the account for a while.",
            "The database is backed up every day; backups are protected and deleted after {backupDays}.",
          ],
        },
        "If a security incident put your data at risk, we would tell the National Cyber Security Authority and, when the law requires it, you.",
      ],
    },
    {
      id: "cookies",
      title: "Cookies and storage on your device",
      body: [
        "Iga uses no advertising, analytics or tracking cookies. It only keeps what it needs to work:",
        {
          list: [
            "iga_refresh: a cookie that keeps you signed in for up to {sessionDays}. Page scripts can't read it, and it is deleted when you log out.",
            "iga_team: a cookie only for Iga team accounts, so that they can reach Iga while it is being updated.",
            "sessionid and csrftoken: cookies only for Iga staff in the content administration area.",
            "In your browser's storage: your language, your theme, whether the menu is hidden, calculator settings, and, so that Iga works offline, a copy of your profile and the lessons you saved. Logging out deletes your profile copy and saved lessons; your language and display settings stay.",
            "Your conversations on the Ask Santa page stay in that browser tab only, and are deleted when you log out or close the tab.",
          ],
        },
        "Because Iga needs these to work, they don't need a separate consent. You can delete them at any time in your browser's settings.",
      ],
    },
    {
      id: "changes",
      title: "Changes to this policy",
      body: [
        "When we change this policy in a way that matters, we change its version date and ask everyone to read and accept the new version the next time they use Iga.",
      ],
    },
    {
      id: "contact",
      title: "Contact us",
      body: ["{entity}, {address}. Email: {email}. You can also use the [contact page](/contact)."],
    },
  ],
};
