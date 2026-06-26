# RSS XML Structure Reference

## Source
https://daily.juya.uk/rss.xml

## Format
RSS 2.0 with content:encoded namespace.

## Extraction
1. Parse XML, get latest `<item>`
2. `<title>` = date
3. `content:encoded` (CDATA HTML) = full content
4. Split by `<hr>` → each block is one story
5. Per block: `<h2><a>` = title+link, `<blockquote>` = summary, `<p>` = body, `<img>` = images
6. Strip B站/YouTube video links
