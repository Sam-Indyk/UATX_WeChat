type Props = {
  size?: number;
  className?: string;
};

/** UATX wordmark + wide W. Same shape as the favicon, inlined here so
 *  callers can size it freely and recolor via `currentColor`. Set a
 *  text color on a parent (or pass `className="text-amber-600"`) and
 *  the mark follows. */
export default function Logo({ size = 32, className }: Props) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      role="img"
      aria-label="UATX"
      className={className}
    >
      <text
        x="32"
        y="26"
        fontFamily="ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif"
        fontSize={22}
        fontWeight={800}
        textAnchor="middle"
        fill="currentColor"
        textLength={56}
        lengthAdjust="spacingAndGlyphs"
      >
        UATX
      </text>
      <path
        d="M 4 34 L 20 58 L 32 44 L 44 58 L 60 34"
        fill="none"
        stroke="currentColor"
        strokeWidth={6}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
