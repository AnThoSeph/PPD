// ATS Minimal — airy whitespace, subtle gray typography
#import "ats-v2-lib.typ": *

#let resume-path = sys.inputs.at("resume")
#let r = load-resume(resume-path)
#let body-size = 10.5pt
#let muted = rgb("#4b5563")

#set page(paper: "a4", margin: 0.65in)
#set text(font: "Segoe UI", size: body-size, fill: rgb("#1f2937"))
#set par(leading: 0.82em, justify: false)

#let section-title(title) = {
  v(1.4em)
  text(size: 9pt, weight: "bold", fill: muted, tracking: 0.14em)[#upper(title)]
  v(0.45em)
}

#text(size: 26pt, weight: "light", tracking: 0.02em)[#r.personal.name]
#if "title" in r.personal and r.personal.title != none and r.personal.title != "" {
  v(0.2em)
  text(size: 11pt, fill: muted)[#r.personal.title]
}
#v(0.5em)
#text(size: 9.5pt, fill: muted)[#contact-parts(r.personal).join("   ·   ")]

#if "summary" in r and "text" in r.summary and r.summary.text != none and r.summary.text != "" {
  section-title("Summary")
  par(leading: 0.85em)[#r.summary.text]
}

#if "experience" in r and r.experience.len() > 0 {
  section-title("Experience")
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
