// ATS Executive — navy accents, authoritative layout
#import "ats-v2-lib.typ": *

#let resume-path = sys.inputs.at("resume")
#let r = load-resume(resume-path)
#let body-size = 10.5pt
#let navy = rgb("#1e3a5f")

#set page(paper: "a4", margin: 0.5in)
#set text(font: "Libertinus Serif", size: body-size, fill: black)
#set par(leading: 0.76em, justify: false)

#let section-title(title) = {
  v(0.95em)
  text(size: 11.5pt, weight: "bold", fill: navy)[#title]
  v(0.08em)
  line(length: 100%, stroke: 0.5pt + navy)
  v(0.32em)
}

#text(size: 27pt, weight: "bold", fill: navy)[#r.personal.name]
#if "title" in r.personal and r.personal.title != none and r.personal.title != "" {
  v(0.12em)
  text(size: 12pt)[#r.personal.title]
}
#v(0.3em)
#text(size: 10pt)[#contact-parts(r.personal).join("  |  ")]
#v(0.25em)
#line(length: 100%, stroke: 0.5pt + navy)
#v(0.05em)
#line(length: 100%, stroke: 2pt + navy)

#if "summary" in r and "text" in r.summary and r.summary.text != none and r.summary.text != "" {
  section-title("Executive Summary")
  par(leading: 0.78em)[#r.summary.text]
}

#if "experience" in r and r.experience.len() > 0 {
  section-title("Professional Experience")
  render-experience(r, body-size)
}

#if "projects" in r and r.projects.len() > 0 {
  section-title("Key Projects")
  render-projects(r, body-size)
}

#if "skills" in r and has-skills(r.skills) {
  section-title("Core Competencies")
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
