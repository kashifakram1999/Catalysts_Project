import { useState } from 'react';
import PageHero from '../components/PageHero';

export default function FAQ() {
  const [openIndex, setOpenIndex] = useState(null);

  const faqs = [
    {
      question: "What states require CARB-approved catalytic converters?",
      answer: "California, New York, Colorado, and Maine require CARB-approved aftermarket catalytic converters. Other states may adopt these requirements in the future."
    },
    {
      question: "What is an Executive Order (EO) number?",
      answer: "An Executive Order number is a unique identifier assigned by CARB to approve aftermarket parts. It verifies that the part meets California's strict emissions standards."
    },
    {
      question: "Can I install a non-CARB converter in California?",
      answer: "No. In California and other CARB states, only CARB-approved converters are legal for installation. Using a non-approved converter can result in failed inspections and fines."
    },
    {
      question: "How often is the data updated?",
      answer: "We regularly scrape data from official CARB sources to ensure our database reflects the latest approvals and Executive Orders."
    },
    {
      question: "What's the difference between Direct-Fit and Universal converters?",
      answer: "Direct-Fit converters are designed for specific vehicle applications with pre-formed pipes and mounting points. Universal converters require custom fitting and welding."
    },
    {
      question: "Do I need a CARB converter if I live in a non-CARB state?",
      answer: "If you don't live in a CARB state, you're not legally required to use a CARB-approved converter. However, CARB converters often meet or exceed federal standards."
    },
    {
      question: "How do I verify the information before purchasing?",
      answer: "Always verify the Executive Order number with your installer and cross-reference with CARB's official database. Check that the EO date is current and the converter matches your vehicle's specifications."
    },
    {
      question: "What if I can't find my vehicle?",
      answer: "Try different search combinations or check the make/model spelling. If your vehicle still doesn't appear, consult directly with CARB or a certified emissions specialist."
    }
  ];

  const toggleFAQ = (index) => {
    setOpenIndex(openIndex === index ? null : index);
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <PageHero
        eyebrow="Need clarity?"
        title="Frequently Asked Questions"
        subtitle="Get quick answers about CARB regulations, Executive Orders, and how to use our lookup tool with confidence."
        alignment="center"
      />

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">

        <div className="space-y-4">
          {faqs.map((faq, index) => (
            <div key={index} className="card overflow-hidden">
              <button
                onClick={() => toggleFAQ(index)}
                className="w-full px-6 py-4 text-left flex justify-between items-center hover:bg-primary-50 dark:hover:bg-primary-700 transition-colors"
              >
                <span className="font-semibold text-primary-900 dark:text-primary-100">
                  {faq.question}
                </span>
                <svg
                  className={`w-5 h-5 text-primary-500 transform transition-transform ${
                    openIndex === index ? 'rotate-180' : ''
                  }`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {openIndex === index && (
                <div className="px-6 py-4 bg-primary-50 dark:bg-primary-900 border-t border-primary-200 dark:border-primary-700">
                  <p className="text-primary-700 dark:text-primary-300">
                    {faq.answer}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
