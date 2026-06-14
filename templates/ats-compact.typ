// ATS Compact — tight single-column, v2 YAML
#let resume-path = sys.inputs.at("resume")
#let root = yaml(resume-path)
#let r = if "resume" in root { root.resume } else { root }

#set page(paper: "a4", margin: 0.35in)
#set text(font: "Libertinus Serif", size: 10pt, fill: black)
#set par(leading: 0.68em, justify: false)

#let contact-parts = {
  let parts = ()
  let p = r.personal
  if "location" in p and p.location != none and p.location != "" { parts.push(p.location) }
  if "phone" in p and p.phone != none and p.phone != "" { parts.push(p.phone) }
  if "email" in p and p.email != none and p.email != "" { parts.push(p.email) }
  if "github" in p and p.github != none and p.github != "" { parts.push("GitHub: " + p.github) }
  if "linkedin" in p and p.linkedin != none and p.linkedin != "" { parts.push("LinkedIn: " + p.linkedin) }
  if "portfolio" in p and p.portfolio != none and p.portfolio != "" { parts.push("Portfolio: " + p.portfolio) }
  parts
}

#let section-title(title) = {
  v(0.55em)
  text(size: 11pt, weight: "bold")[#title]
  v(0.2em)
}

#let exp-dates(item) = {
  let s = if "start_date" in item { item.start_date } else { none }
  let e = if "end_date" in item { item.end_date } else { none }
  if s != none and e != none and s != "YYYY" { [#s – #e] }
  else if s != none and s != "YYYY" { [#s] }
  else if e != none { [#e] }
  else { [] }
}

#align(center)[
  #text(size: 20pt, weight: "bold")[#r.personal.name]
  #v(0.25em)
  #text(size: 9pt)[#contact-parts.join(" | ")]
]

#if "summary" in r and "text" in r.summary and r.summary.text != none and r.summary.text != "" {
  section-title("Professional Summary")
  par(leading: 0.7em)[#r.summary.text]
}

#if "experience" in r and r.experience.len() > 0 {
  section-title("Work Experience")
  for job in r.experience {
    grid(columns: (1fr, auto), gutter: 6pt, text(weight: "bold", size: 10pt)[#job.title], align(right, exp-dates(job)))
    text(size: 9.5pt)[#job.company#if "location" in job and job.location != none { " — " + job.location }]
    v(0.1em)
    for b in job.bullets { par(hanging-indent: 10pt)[• #b] }
    v(0.3em)
  }
}

#if "projects" in r and r.projects.len() > 0 {
  section-title("Projects")
  for proj in r.projects {
    text(weight: "bold", size: 10pt)[#proj.name]
    if "technologies" in proj and proj.technologies.len() > 0 {
      v(0.05em)
      text(size: 9.5pt)[#proj.technologies.join(", ")]
    }
    v(0.08em)
    for b in proj.bullets { par(hanging-indent: 10pt)[• #b] }
    v(0.25em)
  }
}

#if "skills" in r {
  let sk = r.skills
  let groups = (
    ("Frontend", if "frontend" in sk { sk.frontend } else { () }),
    ("Backend", if "backend" in sk { sk.backend } else { () }),
    ("Database", if "database" in sk { sk.database } else { () }),
    ("Cloud & Tools", if "cloud_tools" in sk { sk.cloud_tools } else { () }),
    ("Other", if "other" in sk { sk.other } else { () }),
  )
  let has-skills = false
  for (label, items) in groups {
    if items.len() > 0 { has-skills = true }
  }
  if has-skills {
    section-title("Skills")
    for (label, items) in groups {
      if items.len() > 0 {
        grid(columns: (80pt, 1fr), gutter: 8pt, text(weight: "bold", size: 9.5pt)[#label:], [#items.join(", ")])
        v(0.08em)
      }
    }
  }
}

#if "education" in r and r.education.len() > 0 {
  section-title("Education")
  for edu in r.education {
    text(weight: "bold", size: 10pt)[#edu.degree]
    v(0.05em)
    text(size: 9.5pt)[#edu.institution#if "graduation" in edu and edu.graduation != none { " · " + edu.graduation }]
    v(0.2em)
  }
}

#if "certifications" in r and r.certifications.len() > 0 {
  section-title("Certifications")
  for c in r.certifications { par(hanging-indent: 10pt)[• #c] }
}

#if "custom_sections" in r {
  for sec in r.custom_sections {
    section-title(sec.title)
    for item in sec.items { par(hanging-indent: 10pt)[• #item] }
  }
}
