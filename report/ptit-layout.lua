function RawBlock(el)
  if el.format == 'html' then
    local t = el.text:gsub('%s+', '')
    if t == '<!--PTIT_COVER_PAGE-->' then
      return pandoc.Para({ pandoc.Str('__PTIT_COVER_PAGE__') })
    elseif t == '<!--PTIT_TOC_PLACEHOLDER-->' then
      return pandoc.Para({ pandoc.Str('__PTIT_TOC_PLACEHOLDER__') })
    elseif t == '<!--PTIT_SECTION_MAIN-->' then
      return pandoc.Para({ pandoc.Str('__PTIT_SECTION_MAIN__') })
    end
  end
  return nil
end

function Para(el)
  -- Tag italic table caption lines (*Bảng X.Y. ...*) for custom-style="TableCaption"
  if #el.content == 1 and el.content[1].t == 'Emph' then
    local txt = pandoc.utils.stringify(el)
    if txt:match('^Bảng%s+%d') or txt:match('^Bảng%s+[A-Z]%.') then
      return pandoc.Div({ pandoc.Para(el.content) }, pandoc.Attr('', {}, { ['custom-style'] = 'Table Caption' }))
    end
  end
  return nil
end

function CodeBlock(el)
  if #el.classes == 0 then
    el.classes = { 'text' }
  end
  return el
end
