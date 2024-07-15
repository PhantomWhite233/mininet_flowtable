graph [
  directed 1
  node [
    id 0
    label "h1"
    type "host"
    mac "00:00:00:00:00:01"
    ip "10.0.0.1"
  ]
  node [
    id 1
    label "s1"
    type "switch"
  ]
  node [
    id 2
    label "h2"
    type "host"
    mac "00:00:00:00:00:02"
    ip "10.0.0.2"
  ]
  node [
    id 3
    label "s2"
    type "switch"
  ]
  node [
    id 4
    label "h3"
    type "host"
    mac "00:00:00:00:00:03"
    ip "10.0.0.3"
  ]
  node [
    id 5
    label "s3"
    type "switch"
  ]
  node [
    id 6
    label "h4"
    type "host"
    mac "00:00:00:00:00:04"
    ip "10.0.0.4"
  ]
  edge [
    source 0
    target 1
    port 1
  ]
  edge [
    source 1
    target 0
    port 1
  ]
  edge [
    source 1
    target 2
    port 2
  ]
  edge [
    source 2
    target 1
    port 1
  ]
  edge [
    source 3
    target 4
    port 1
  ]
  edge [
    source 4
    target 3
    port 1
  ]
  edge [
    source 6
    target 5
    port 1
  ]
  edge [
    source 5
    target 6
    port 1
  ]
  edge [
    source 1
    target 3
    port 10
  ]
  edge [
    source 3
    target 1
    port 11
  ]
  edge [
    source 3
    target 5
    port 12
  ]
  edge [
    source 5
    target 3
    port 13
  ]
]