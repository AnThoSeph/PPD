// ATS Elegant — refined serif, centered header, classic feel
#import "ats-v2-lib.typ": *

#let resume-path = sys.inputs.at("resume")
#let r = load-resume(resume-path)
#let body-size = 10.5pt

#set page(paper: "a4", margin: 0.55in)
#set text(font: "Libertinus Serif", size: body-size, fill: black)
#set par(leading: 0.78em, justify: false)

#let section-title(title) = {
  v(1em)
  align(center)[#text(size: 12pt, weight: "bold", style: "italic")[#title]]
  v(0.1em)
  align(center)[#line(length: 35%, stroke: 0.75pt + black)]
  v(0.35em)
}

#align(center)[
  #text(size: 28pt, weight: "bold")[#r.personal.name]
  #if "title" in r.personal and r.personal.title != none and r.personal.title != "" {
    v(0.15em)
    text(size: 12pt, style: "italic")[#r.personal.title]
  }
  #v(0.35em)
  #text(size: 10pt)[#contact-parts(r.personal).join(" · ")]
]

#if "summary" in r and "text" in r.summary and r.summary.text != none and r.summary.text != "" {
  section-title("Professional Summary")
  par(leading: 0.8em)[#r.summary.text]
}

#if "experience" in r and r.experience.len() > 0 {
  section-title("Work Experience")
  render-experience(r, body-size)
}

#if "projects" in r and r.projects.len() > 0 {
  section-title("Projects")
  render-projects(r, body-size)
}

#if "skills" in r and has-skills(r.skills) {
  section-title("Skills")
  render-skills-inline(r, body-size)
}

#if "education" in r and r.education.len() > 0 {
  section-title("Education")
  render-education(r, body-size)
}

#if "certifications" in r and r.certifications.len() > 0 {
  section-title("Certifications")
  render-certs(r)
}

#if "custom_sections" in r {
  for sec in r.custom_sections {
    section-title(sec.title)
    for item in sec.items { par(hanging-indent: 12pt)[• #item] }
  }
}
