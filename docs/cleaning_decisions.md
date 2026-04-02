# Data Cleaning Decisions

This document explains the data cleaning decisions made in the Tech Pulse pipeline.

## Overview

Raw scraped data from multiple sources requires cleaning and standardization before storage. Our cleaning pipeline handles:

1. Deduplication
2. Missing value handling
3. Text normalization
4. Date standardization
5. Category mapping
6. Tag cleaning

## Cleaning Decisions

### 1. Deduplication Strategy

**Decision**: Remove duplicates based on URL (primary) and similar titles (secondary)

**Rationale**:
- URL is the most reliable unique identifier for articles
- Similar titles (>90% word overlap) likely represent the same news from different sources
- We keep the first occurrence (usually the most recent scrape)

**Implementation**:
- Normalize URLs by removing trailing slashes, query params, and fragments
- Create title "hash" from first 5 significant words (>3 chars)

### 2. Missing Value Handling

**Decision**: Different strategies for required vs optional fields

| Field | Strategy | Default Value |
|-------|----------|---------------|
| title | **Required** - drop if missing | N/A |
| url | **Required** - drop if missing | N/A |
| author | Optional - use default | "Unknown" |
| category | Optional - use default | "Tech News" |
| summary | Optional - allow empty | "" |
| content | Optional - allow empty | "" |
| tags | Optional - use empty list | [] |
| published_at | Optional - use scraped_at | scraped_at value |

**Rationale**:
- Title and URL are essential for article identity
- Other fields enhance data but aren't critical
- Using defaults ensures consistent data structure

### 3. Date Standardization

**Decision**: Convert all dates to UTC ISO 8601 format

**Supported Input Formats**:
- ISO 8601: `2025-01-15T10:30:00Z`
- ISO without timezone: `2025-01-15T10:30:00`
- Date only: `2025-01-15`
- Human readable: `January 15, 2025`, `Jan 15, 2025`
- RSS format: `Wed, 15 Jan 2025 10:30:00`

**Output Format**: `2025-01-15T10:30:00Z`

**Rationale**:
- ISO 8601 is universally parseable
- UTC avoids timezone confusion
- Consistent format enables proper sorting and filtering

### 4. Text Normalization

**Decision**: Clean text while preserving content

**Operations**:
1. Remove HTML entities (`&amp;`, `&#39;`, etc.)
2. Normalize whitespace (multiple spaces → single space)
3. Remove control characters (non-printable)
4. Strip leading/trailing whitespace

**Not Done**:
- Case normalization (preserve original casing)
- Special character removal (may be meaningful)
- Truncation (stored in full)

**Rationale**:
- HTML entities are artifacts from web scraping
- Whitespace normalization improves readability
- Preserve original content as much as possible

### 5. Category Standardization

**Decision**: Map various category names to standard values

**Category Mapping**:

| Input Variations | Standard Category |
|-----------------|-------------------|
| ai, artificial intelligence, machine learning, deep learning, llm | AI/ML |
| funding, startups, venture capital, acquisition, ipo | Funding |
| product launch, product, launch | Product Launch |
| security, cybersecurity, privacy | Security |
| open source, github, repository | Open Source |
| web development, frontend, backend, devops | Development |
| tech news, general | Tech News |
| enterprise | Enterprise |
| gaming | Gaming |

**Rationale**:
- Reduces category fragmentation
- Enables meaningful filtering
- Maintains business relevance

### 6. Tag Cleaning

**Decision**: Normalize and deduplicate tags

**Operations**:
1. Convert to lowercase
2. Remove special characters (keep alphanumeric, spaces, hyphens)
3. Remove duplicates
4. Filter out tags with <2 characters
5. Limit to 10 tags per article

**Rationale**:
- Consistent tag format improves searchability
- Deduplication prevents redundancy
- Character limit ensures meaningful tags
- Count limit prevents tag spam

### 7. URL Validation

**Decision**: Remove articles with invalid URLs

**Valid URL Criteria**:
- Must have http:// or https:// scheme
- Must have a valid domain (netloc)

**Rationale**:
- Invalid URLs provide no value
- External links are essential for article access

## Derived Fields

Fields computed during cleaning:

| Field | Computation |
|-------|-------------|
| content_length | Length of content string |
| has_content | True if content_length > 100 |
| hash_id | MD5 hash of URL (first 12 chars) |

## Trade-offs

1. **Aggressive vs Conservative Deduplication**
   - Chose moderate approach: URL-based + similar titles
   - Trade-off: May occasionally keep near-duplicates vs losing unique articles

2. **Category Mapping**
   - Chose predefined mapping vs automatic clustering
   - Trade-off: Simpler/predictable vs potentially more accurate grouping

3. **Missing Value Defaults**
   - Chose explicit defaults vs NULL/None
   - Trade-off: Data consistency vs potential false information

## Future Improvements

1. **Fuzzy Deduplication**: Use similarity scores for more accurate duplicate detection
2. **ML Category Classification**: Train a model for automatic categorization
3. **Entity Extraction**: Extract company names, people, technologies as tags
4. **Language Detection**: Filter/tag non-English content
5. **Quality Scoring**: Assign quality scores based on content completeness
