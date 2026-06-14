// Single-column ATS-friendly template
#let resume-path = sys.inputs.at("resume")
#let data = yaml(resume-path)

#set page(paper: "a4", margin: (x: 18mm, y: 16mm))
#set text(font: "Segoe UI", size: 10.5pt)

#let section-title(content) = {
  v(0.5em)
  text(size: 12pt, weight: "bold")[#upper(content)]
  v(0.2em)
  line(length: 100%, stroke: 0.5pt)
  v(0.3em)
}

#align(center)[
  #text(size: 22pt, weight: "bold")[#data.basics.name]
  #if "title" in data.basics and data.basics.title != none { linebreak(); text(size: 11pt)[#data.basics.title] }
  #v(0.2em)
  #text(size: 9.5pt)[
    #if "email" in data.basics { data.basics.email }
    #if "phone" in data.basics { " | " + data.basics.phone }
    #if "location" in data.basics { " | " + data.basics.location }
  ]
]

#if "summary" in data and data.summary != none {
  section-title("Summary")
  data.summary
}

#let job-dates(job) = {
  if "start" in job and "end" in job { [#job.start - #job.end] }
  else if "start" in job { [#job.start] }
  else if "end" in job { [#job.end] }
  else { [] }
}

#if "experience" in data {
  section-title("Experience")
  for job in data.experience {
    strong(job.role) + " - " + job.company
    h(1fr, align(right, text(size: 9pt)[#job-dates(job)]))
    if "bullets" in job {
      for b in job.bullets { [- #b] }
    }
    v(0.3em)
  }
}

#if "education" in data {
  section-title("Education")
  for edu in data.education {
    strong(edu.degree) + " - " + edu.institution
    v(0.2em)
  }
}

#if "skills" in data {
  section-title("Skills")
  for g in data.skills {
    strong(g.category + ": ") + g.items.join(", ")
    v(0.15em)
  }
}
