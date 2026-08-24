module ApplicationHelper
  def points(amount)
    number_with_delimiter(amount.to_i)
  end

  def pool_percent(probability)
    "#{(probability.to_f * 100).round(1)}%"
  end

  def tag_label(tag)
    tag.to_s.tr("_", " ")
  end
end
