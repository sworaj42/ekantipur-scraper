# Ekantipur.com Site Inspection Notes

## Entertainment Section
- URL: https://ekantipur.com/entertainment
- Nav link text (Nepali): मनोरञ्जन

## Page-Level Data
- Category selector: .category-name p a (extract once, use for all articles)

## Article Cards
- Card container selector: .category-inner-wrapper
- Title selector (inside card): .category-description h2 a
- Image selector (inside card): .category-image a figure img (use data-src for lazy loaded, fallback to src)
- Author selector (inside card): .author-name p a (some cards have multiple authors)

- URL: https://ekantipur.com/cartoon
- Cartoon container: .cartoon-wrapper (first one = today's cartoon)
- Title: img alt attribute inside .cartoon-image figure
- Image URL: img src or data-src inside .cartoon-image figure
- Author: .cartoon-description p text, split by " - " to get author name

## Expected Output Format
{
  "entertainment_news": [
    {"title": "...", "image_url": "...", "category": "...", "author": "..."}
  ],
  "cartoon_of_the_day": {
    "title": "...", "image_url": "...", "author": "..."
  }
}