function Table(t)
  -- Replace all column alignments with simple left-aligned
  for i, col in ipairs(t.colspecs) do
    t.colspecs[i] = {pandoc.AlignLeft, nil}
  end
  return t
end