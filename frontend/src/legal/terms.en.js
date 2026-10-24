// The Terms of Use, in English (terms.fr.js is the French text; both must keep the same sections).
// A DRAFT for a lawyer to review before launch: the page says so while the server's LEGAL_DRAFT_NOTICE is on.
// {placeholders} come from the server (/api/site/): entity, address, email, santaDays, subscriptionGraceDays.
// [text](/path) is a link to a page of the app. Raise LEGAL_VERSION on the server when the meaning changes.
export default {
  title: "Terms of Use",
  intro: [
    "These terms are the agreement between you and {entity} for using Iga, the learning app for Rwanda's secondary schools. Please read them together with the [Privacy Policy](/privacy).",
    "By creating an account or using Iga, you accept these terms. If you are under 16, a parent or guardian must read them with you and agree.",
  ],
  sections: [
    {
      id: "about",
      title: "What Iga is",
      body: [
        "Iga gives students lessons that follow Rwanda's competence-based curriculum, virtual labs, practice quizzes and past papers, a calculator, a code playground and Santa, an AI tutor. Teachers can run classes and set and mark work, parents can follow their child's progress, and schools manage their members and pay a subscription.",
        "Starter lessons are free for everyone with an account. The full library is for members of schools with an active subscription.",
      ],
    },
    {
      id: "account",
      title: "Your account",
      body: [
        {
          list: [
            "Give true information and keep your password secret. You are responsible for what is done with your account.",
            "One account per person. Don't use someone else's account.",
            "An account created by a teacher starts with a temporary password: choose your own at your first sign-in.",
            "Teacher tools open once your school or the Iga team approves your teacher account, because classes contain children.",
            "If you think someone else is using your account, tell us at once at {email}. You can log out on every device from your profile.",
          ],
        },
      ],
    },
    {
      id: "children",
      title: "Children",
      body: [
        "Iga is made for secondary school students, and many of them are under 16. A student under 16 may only use Iga with the agreement of a parent or guardian, or of their school when the school created the account with the parents' consent. Parents and guardians are responsible for their child's use of Iga outside school.",
      ],
    },
    {
      id: "conduct",
      title: "Using Iga well",
      body: [
        "You agree not to:",
        {
          list: [
            "bully, threaten or insult anyone, or share inappropriate content, in groups or anywhere else;",
            "share other people's personal information;",
            "cheat: share the answers to timed tests or exams, or let someone else sit them for you;",
            "try to get into accounts or parts of Iga you are not allowed to use, overload Iga, or get around its limits or its security;",
            "upload anything illegal or harmful, or anything you don't have the right to share;",
            "use Iga to advertise or sell anything.",
          ],
        },
        "Anyone can report a message, and reports are reviewed by teachers and the Iga team. We may hide content, and suspend accounts that break these rules.",
      ],
    },
    {
      id: "santa",
      title: "Santa, the AI tutor",
      body: [
        "Santa explains ideas and gives hints using Iga's lessons. It runs on Iga's own server. Like every AI, Santa can make mistakes: check important answers with your lessons or your teacher.",
        "Santa is switched off while you sit a timed test or an exam, and daily limits apply. Questions and answers are kept for {santaDays} so that the Iga team can check that Santa is safe and helpful.",
      ],
    },
    {
      id: "schools",
      title: "Schools and subscriptions",
      body: [
        {
          list: [
            "A school administrator accepts these terms for their school, and confirms that they are allowed to act for it.",
            "The subscription price is the one shown on Iga's pricing section and on the school's billing page when you pay. It covers every approved member of the school for the months paid. Prices may change, but a change never affects months already paid.",
            "Schools pay by card or mobile money through Flutterwave, or by bank transfer recorded by the Iga team. A subscription does not renew by itself: the school pays again to continue. When it ends, access continues for a grace period of {subscriptionGraceDays}, then members return to the free lessons. Their accounts and progress are kept.",
            "Payments are not refunded, except where the law requires it or the Iga team agrees in writing. Contact us about any problem with a payment.",
          ],
        },
      ],
    },
    {
      id: "content",
      title: "Content and intellectual property",
      body: [
        {
          list: [
            "Iga's lessons, quizzes, design and software belong to {entity} or to their authors and licensors. You may use them for your own learning and teaching, but not copy them to sell or publish elsewhere.",
            "Some material comes from others under their own licences: PhET simulations (University of Colorado Boulder, CC BY 4.0), GeoGebra (under GeoGebra's terms), and books from the Rwanda Basic Education Board and open textbook publishers.",
            "You keep the rights to what you create on Iga: answers, messages, notes, and the lessons and quizzes a teacher writes. You allow Iga to keep it and show it to the people it is meant for (your teacher, your group, your class). Teachers allow Iga to keep the lessons and quizzes they wrote available to classes, even after they leave.",
          ],
        },
      ],
    },
    {
      id: "availability",
      title: "Availability",
      body: [
        "We work to keep Iga available and your data safe, but we can't promise that Iga will always work without interruption. Iga may be unavailable during updates (it then shows a \"back soon\" page), and its features may change. Lessons you save keep working offline.",
      ],
    },
    {
      id: "ending",
      title: "Ending your use of Iga",
      body: [
        "You can stop using Iga at any time and delete your account from your profile (Privacy). We may suspend or close an account that seriously or repeatedly breaks these terms, or when the law requires it. When we can, we tell you first and explain why.",
      ],
    },
    {
      id: "liability",
      title: "Responsibility",
      body: [
        "Iga helps you learn; it does not replace your teachers or your school. As far as Rwandan law allows, {entity} is not responsible for indirect losses, such as exam results, or for problems caused by things outside our control, such as power or internet cuts or your device. Nothing in these terms takes away the rights you have under Rwandan consumer law.",
      ],
    },
    {
      id: "changes",
      title: "Changes to these terms",
      body: [
        "We may update these terms. When a change matters, we change the version date and ask you to read and accept the new terms before you continue. If you don't accept them, you can delete your account.",
      ],
    },
    {
      id: "law",
      title: "Law and disputes",
      body: [
        "These terms are governed by the laws of the Republic of Rwanda. If we disagree, let's first try to solve it together: write to {email}. If we can't, the competent courts of Rwanda will decide.",
      ],
    },
    {
      id: "contact",
      title: "Contact",
      body: ["{entity}, {address}. Email: {email}. You can also use the [contact page](/contact)."],
    },
  ],
};
