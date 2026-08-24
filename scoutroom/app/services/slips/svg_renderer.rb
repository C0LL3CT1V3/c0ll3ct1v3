module Slips
  class SvgRenderer
    WIDTH = 1080
    HEIGHT = 1920
    SAFE_X = 72
    SAFE_Y = 160

    def initialize(slip)
      @slip = slip
      @prediction = slip.prediction
      @market = @prediction.market
      @artist = @market.artist
      @bytes = [ slip.seed ].pack("H*").bytes
    end

    def render
      <<~SVG
        <svg xmlns="http://www.w3.org/2000/svg" width="#{WIDTH}" height="#{HEIGHT}" viewBox="0 0 #{WIDTH} #{HEIGHT}">
          <defs>
            <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stop-color="#{palette[0]}"/>
              <stop offset="100%" stop-color="#{palette[1]}"/>
            </linearGradient>
            <clipPath id="frame">
              <rect x="#{SAFE_X}" y="#{SAFE_Y}" width="#{WIDTH - SAFE_X * 2}" height="#{HEIGHT - SAFE_Y * 2}" rx="36"/>
            </clipPath>
          </defs>
          <rect width="#{WIDTH}" height="#{HEIGHT}" fill="#0c0b09"/>
          <rect x="#{SAFE_X}" y="#{SAFE_Y}" width="#{WIDTH - SAFE_X * 2}" height="#{HEIGHT - SAFE_Y * 2}" rx="36" fill="url(#bg)"/>
          <g clip-path="url(#frame)" fill="none" stroke="#{palette[2]}" stroke-width="3" opacity="0.85">
            #{waveform_path}
          </g>
          <rect x="#{SAFE_X + 24}" y="#{SAFE_Y + 24}" width="#{WIDTH - SAFE_X * 2 - 48}" height="#{HEIGHT - SAFE_Y * 2 - 48}" rx="24" fill="none" stroke="#f4e8d0" stroke-width="2" opacity="0.55"/>
          <text x="540" y="280" text-anchor="middle" fill="#f4e8d0" font-family="Georgia, serif" font-size="28" letter-spacing="8">SCOUTROOM</text>
          <text x="540" y="420" text-anchor="middle" fill="#f4e8d0" font-family="Georgia, serif" font-size="56">#{escape(@artist.name)}</text>
          <text x="540" y="520" text-anchor="middle" fill="#d9c7a3" font-family="ui-sans-serif, system-ui" font-size="28">#{escape(@market.question)}</text>
          <text x="540" y="720" text-anchor="middle" fill="#f4e8d0" font-family="Georgia, serif" font-size="120" font-weight="700">#{@prediction.side.upcase}</text>
          <text x="540" y="820" text-anchor="middle" fill="#d9c7a3" font-family="ui-sans-serif, system-ui" font-size="32">#{@prediction.points_staked} points · #{(100 * @prediction.implied_probability_at_entry).round(1)}% of pool</text>
          <text x="540" y="980" text-anchor="middle" fill="#f4e8d0" font-family="ui-sans-serif, system-ui" font-size="26">#{percentile_label}</text>
          <text x="540" y="1100" text-anchor="middle" fill="#d9c7a3" font-family="Georgia, serif" font-size="30">#{escape(thesis)}</text>
          <text x="540" y="1680" text-anchor="middle" fill="#a89474" font-family="ui-sans-serif, system-ui" font-size="22">@#{escape(@prediction.user.handle)} · points have no cash value</text>
          <text x="540" y="1736" text-anchor="middle" fill="#a89474" font-family="ui-sans-serif, system-ui" font-size="18">#{@slip.seed[0, 12]}</text>
        </svg>
      SVG
    end

    private

    def palette
      tones = [
        [ "#1a140c", "#3d2a16", "#e8c07a" ],
        [ "#14181a", "#24343a", "#9ad0c8" ],
        [ "#1a1014", "#3a1828", "#e89ab0" ]
      ]
      tones[@bytes[0] % tones.size]
    end

    def waveform_path
      points = 48
      mid_y = 1400
      step = (WIDTH - SAFE_X * 2) / (points - 1).to_f
      coords = Array.new(points) do |i|
        amp = 40 + (@bytes[i % @bytes.size] % 180)
        phase = @bytes[(i + 3) % @bytes.size] / 255.0 * Math::PI * 2
        x = SAFE_X + i * step
        y = mid_y + Math.sin(i / 4.0 + phase) * amp
        "#{x.round(1)},#{y.round(1)}"
      end
      %(<polyline points="#{coords.join(' ')}"/>)
    end

    def percentile_label
      pct = (@slip.discovery_percentile.to_f * 100).round
      "#{pct}% of callers entered after this slip"
    end

    def thesis
      @slip.thesis_text.presence || Array(@slip.thesis_tags).first.to_s.tr("_", " ")
    end

    def escape(text)
      ERB::Util.html_escape(text.to_s)
    end
  end
end
