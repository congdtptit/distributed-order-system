-- Keep tall diagrams on one page: an image more than 1.3 times as tall as it is wide gets a
-- height of 21 cm, so Word does not cut it at the bottom of an A4 page. Used by build.sh.
function Image(img)
  if img.attributes.width or img.attributes.height then
    return nil
  end
  local _, contents = pandoc.mediabag.fetch(img.src)
  if not contents then
    return nil
  end
  local ok, size = pcall(pandoc.image.size, contents)
  if ok and size.height > 1.3 * size.width then
    img.attributes.height = "21cm"
    return img
  end
  return nil
end

-- Convert HTML comment <!--PAGEBREAK--> into a Word page break while keeping Markdown clean.
function RawBlock(el)
  if el.format == "html" and el.text:match("^%s*<!%-%-%s*PAGEBREAK%s*%-%->%s*$") then
    return pandoc.RawBlock("openxml", '<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
  end
end
