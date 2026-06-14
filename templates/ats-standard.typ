// ATS-standard resume — single column, black on white, v2 YAML schema
#let resume-path = sys.inputs.at("resume")
#let root = yaml(resume-path)
#let r = if "resume" in root { root.resume } else { root }

#set page(paper: "a4", margin: 0.5in)
#set text(font: "Libertinus Serif", size: 10.5pt, fill: black)
#set par(leading: 0.72em, justify: false)

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
  v(0.85em)
  text(size: 12pt, weight: "bold")[#title]
  v(0.35em)
}

#let exp-dates(item) = {
  let s = if "start_date" in item { item.start_date } else { none }
  let e = if "end_date" in item { item.end_date } else { none }
  if s != none and e != none and s != "YYYY" {
    [#s – #e]
  } else if s != none and s != "YYYY" {
    [#s]
  } else if e != none {
    [#e]
  } else {
    []
  }
}

#align(center)[
  #text(size: 22pt, weight: "bold")[#r.personal.name]
  #if "title" in r.personal and r.personal.title != none and r.personal.title != "" {
    v(0.2em)
    text(size: 11pt)[#r.personal.title]
  }
  #v(0.35em)
  #text(size: 9.5pt)[#contact-parts.join(" | ")]
]

#if "summary" in r and "text" in r.summary and r.summary.text != none and r.summary.text != "" {
  section-title("Professional Summary")
  par(leading: 0.75em)[#r.summary.text]
}

#if "experience" in r and r.experience.len() > 0 {
  section-title("Work Experience")
  for job in r.experience {
    grid(
      columns: (1fr, auto),
      gutter: 8pt,
      text(weight: "bold")[#job.title],
      align(right, exp-dates(job)),
    )
    let cl = job.company
    if "location" in job and job.location != none and job.location != "" {
      cl = cl + " — " + job.location
    }
    text(size: 10pt)[#cl]
    v(0.15em)
    if "bullets" in job {
      for b in job.bullets {
        par(hanging-indent: 12pt)[• #b]
      }
    }
    v(0.45em)
  }
}

#if "projects" in r and r.projects.len() > 0 {
  section-title("Projects")
  for proj in r.projects {
    text(weight: "bold")[#proj.name]
    if "technologies" in proj and proj.technologies.len() > 0 {
      v(0.1em)
      text(size: 10pt)[#proj.technologies.join(", ")]
    } else if "description" in proj and proj.description != none {
      v(0.1em)
      text(size: 10pt)[#proj.description]
    }
    v(0.12em)
    if "bullets" in proj {
      for b in proj.bullets {
        par(hanging-indent: 12pt)[• #b]
      }
    }
    v(0.4em)
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
        grid(
          columns: (90pt, 1fr),
          gutter: 10pt,
          text(weight: "bold")[#label:],
          [#items.join(", ")],
        )
        v(0.15em)
      }
    }
  }
}

#if "education" in r and r.education.len() > 0 {
  section-title("Education")
  for edu in r.education {
    text(weight: "bold")[#edu.degree#if "field" in edu and edu.field != none and edu.field != "" { " in " + edu.field }]
    v(0.08em)
    text(size: 10pt)[#edu.institution]
    if "location" in edu and edu.location != none and edu.location != "" {
      v(0.05em)
      text(size: 10pt)[#edu.location]
    }
    if "graduation" in edu and edu.graduation != none and edu.graduation != "" {
      v(0.05em)
      text(size: 10pt)[#edu.graduation]
    }
    if "gpa" in edu and edu.gpa != none and edu.gpa != "" {
      v(0.05em)
      text(size: 10pt)[#edu.gpa]
    }
    v(0.35em)
  }
}

#if "certifications" in r and r.certifications.len() > 0 {
  section-title("Certifications")
  for c in r.certifications {
    par(hanging-indent: 12pt)[• #c]
  }
}

#if "custom_sections" in r {
  for sec in r.custom_sections {
    section-title(sec.title)
    for item in sec.items {
      par(hanging-indent: 12pt)[• #item]
    }
  }
}
