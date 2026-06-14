// ATS Creative — contemporary layout, split header band (text-only, ATS-safe)
#import "ats-v2-lib.typ": *

#let resume-path = sys.inputs.at("resume")
#let r = load-resume(resume-path)
#let body-size = 10.5pt
#let ink = rgb("#18181b")
#let warm = rgb("#7c2d12")

#set page(paper: "a4", margin: (x: 0.5in, top: 0.42in, bottom: 0.5in))
#set text(font: "Segoe UI", size: body-size, fill: ink)
#set par(leading: 0.74em, justify: false)

#let section-title(title) = {
  v(0.85em)
  grid(
    columns: (3pt, 1fr),
    gutter: 8pt,
    rect(width: 3pt, height: 1.1em, fill: warm),
    text(size: 11.5pt, weight: "bold")[#title],
  )
  v(0.28em)
}

#block(
  width: 100%,
  inset: (x: 0pt, y: 12pt),
  stroke: (bottom: 1.5pt + warm),
)[
  #grid(
    columns: (2fr, 1fr),
    gutter: 16pt,
    [
      #text(size: 28pt, weight: "bold")[#r.personal.name]
      #if "title" in r.personal and r.personal.title != none and r.personal.title != "" {
        v(0.1em)
        text(size: 11.5pt, fill: warm)[#r.personal.title]
      }
    ],
    align(right + horizon)[
      #text(size: 9pt)[
        #for (i, part) in contact-parts(r.personal).enumerate() [
          #if i > 0 [ \ ]
          #part
        ]
      ]
    ],
  )
]

#if "summary" in r and "text" in r.summary and r.summary.text != none and r.summary.text != "" {
  section-title("Professional Summary")
  par(leading: 0.76em)[#r.summary.text]
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
