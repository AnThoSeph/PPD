// Shared v2 resume helpers for ATS templates
#let load-resume(path) = {
  let root = yaml(path)
  if "resume" in root { root.resume } else { root }
}

#let contact-parts(p) = {
  let parts = ()
  if "location" in p and p.location != none and p.location != "" { parts.push(p.location) }
  if "phone" in p and p.phone != none and p.phone != "" { parts.push(p.phone) }
  if "email" in p and p.email != none and p.email != "" { parts.push(p.email) }
  if "github" in p and p.github != none and p.github != "" { parts.push(p.github) }
  if "linkedin" in p and p.linkedin != none and p.linkedin != "" { parts.push(p.linkedin) }
  if "portfolio" in p and p.portfolio != none and p.portfolio != "" { parts.push(p.portfolio) }
  parts
}

#let exp-dates(item) = {
  let s = if "start_date" in item { item.start_date } else { none }
  let e = if "end_date" in item { item.end_date } else { none }
  if s != none and e != none and s != "YYYY" { [#s – #e] }
  else if s != none and s != "YYYY" { [#s] }
  else if e != none { [#e] }
  else { [] }
}

#let skill-groups(sk) = (
  ("Frontend", if "frontend" in sk { sk.frontend } else { () }),
  ("Backend", if "backend" in sk { sk.backend } else { () }),
  ("Database", if "database" in sk { sk.database } else { () }),
  ("Cloud & Tools", if "cloud_tools" in sk { sk.cloud_tools } else { () }),
  ("Other", if "other" in sk { sk.other } else { () }),
)

#let has-skills(sk) = {
  let groups = skill-groups(sk)
  let found = false
  for (label, items) in groups { if items.len() > 0 { found = true } }
  found
}

#let render-experience(r, body-size) = {
  if "experience" in r and r.experience.len() > 0 {
    for job in r.experience {
      grid(
        columns: (1fr, auto),
        gutter: 8pt,
        text(size: body-size, weight: "bold")[#job.title],
        align(right, text(size: body-size)[#exp-dates(job)]),
      )
      let cl = job.company
      if "location" in job and job.location != none and job.location != "" {
        cl = cl + " — " + job.location
      }
      text(size: body-size)[#cl]
      v(0.12em)
      if "bullets" in job {
        for b in job.bullets { par(hanging-indent: 12pt)[• #b] }
      }
      v(0.4em)
    }
  }
}

#let render-projects(r, body-size) = {
  if "projects" in r and r.projects.len() > 0 {
    for proj in r.projects {
      text(weight: "bold", size: body-size)[#proj.name]
      if "technologies" in proj and proj.technologies.len() > 0 {
        v(0.08em)
        text(size: body-size)[#proj.technologies.join(", ")]
      }
      v(0.1em)
      if "bullets" in proj {
        for b in proj.bullets { par(hanging-indent: 12pt)[• #b] }
      }
      v(0.35em)
    }
  }
}

#let render-skills-inline(r, body-size) = {
  if "skills" in r and has-skills(r.skills) {
    for (label, items) in skill-groups(r.skills) {
      if items.len() > 0 {
        grid(
          columns: (95pt, 1fr),
          gutter: 10pt,
          text(weight: "bold", size: body-size)[#label + ":"],
          [#items.join(", ")],
        )
        v(0.12em)
      }
    }
  }
}

#let render-education(r, body-size) = {
  if "education" in r and r.education.len() > 0 {
    for edu in r.education {
      text(weight: "bold", size: body-size)[#edu.degree]
      v(0.06em)
      text(size: body-size)[#edu.institution#if "graduation" in edu and edu.graduation != none { " · " + edu.graduation }]
      v(0.28em)
    }
  }
}

#let render-certs(r) = {
  if "certifications" in r and r.certifications.len() > 0 {
    for c in r.certifications { par(hanging-indent: 12pt)[• #c] }
  }
}

#let render-custom(r) = {
  if "custom_sections" in r {
    for sec in r.custom_sections {
      for item in sec.items { par(hanging-indent: 12pt)[• #item] }
    }
  }
}

// Render resume sections in the order given by visible_sections.
// section-title is a template-specific function(body-size, title) => content.
// Title overrides let templates customize section headings (e.g. "Profile" vs "Summary").
#let render-ordered-sections(
  r,
  section-title,
  body-size,
  summary-title: "Professional Summary",
  experience-title: "Work Experience",
  projects-title: "Projects",
  skills-title: "Skills",
  education-title: "Education",
  certifications-title: "Certifications",
) = {
  let sections = if "visible_sections" in r { r.visible_sections } else { () }
  // Fallback when visible_sections is missing or empty
  if sections.len() == 0 {
    sections = ("summary", "experience", "projects", "skills", "education", "certifications")
    if "custom_sections" in r and r.custom_sections.len() > 0 { sections += ("custom_sections",) }
  }
  for sec in sections {
    // Skip personal — rendered as the header block
    if sec == "personal" { continue }

    // Legacy: single "custom_sections" key renders all custom sections in order
    if sec == "custom_sections" and "custom_sections" in r {
      for cs in r.custom_sections {
        if cs.items.len() > 0 {
          section-title(cs.title)
          for item in cs.items { par(hanging-indent: 12pt)[• #item] }
        }
      }
      continue
    }

    // New format: custom_N maps to custom_sections[N]
    if sec.starts-with("custom_") and "custom_sections" in r {
      let idx = int(sec.slice(7))
      if idx < r.custom_sections.len() and r.custom_sections.at(idx).items.len() > 0 {
        let cs = r.custom_sections.at(idx)
        section-title(cs.title)
        for item in cs.items { par(hanging-indent: 12pt)[• #item] }
      }
      continue
    }

    // Standard built-in sections
    if sec == "summary" and "summary" in r and "text" in r.summary and r.summary.text != none and r.summary.text != "" {
      section-title(summary-title)
      par(leading: 0.75em)[#r.summary.text]
    } else if sec == "experience" and "experience" in r and r.experience.len() > 0 {
      section-title(experience-title)
      render-experience(r, body-size)
    } else if sec == "projects" and "projects" in r and r.projects.len() > 0 {
      section-title(projects-title)
      render-projects(r, body-size)
    } else if sec == "skills" and "skills" in r and has-skills(r.skills) {
      section-title(skills-title)
      render-skills-inline(r, body-size)
    } else if sec == "education" and "education" in r and r.education.len() > 0 {
      section-title(education-title)
      render-education(r, body-size)
    } else if sec == "certifications" and "certifications" in r and r.certifications.len() > 0 {
      section-title(certifications-title)
      render-certs(r)
    }
  }
}
