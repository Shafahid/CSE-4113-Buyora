"use client";

import Link from "next/link";
import Image from "next/image";
import { CountUp } from "./count-up";
import {
  createContext,
  useContext,
  useEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { Persona, Product } from "@/lib/demo-data";

const paths: Record<string, string> = {
  arrow: "M4 12h16m-6-6 6 6-6 6",
  chevron: "m9 5 7 7-7 7",
  back: "M20 12H4m6-6-6 6 6 6",
  plus: "M12 5v14M5 12h14",
  grid: "M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z",
  box: "m12 3 9 5-9 5-9-5 9-5Zm-9 5v9l9 5 9-5V8M12 13v9M7.5 5.5l9 5",
  file: "M14 2H5v20h14V7l-5-5Zm0 0v6h5M8 12h8M8 16h6",
  play: "m9 5 11 7-11 7V5Z",
  history: "M3 11a9 9 0 1 1 2 7M3 4v7h7M12 7v5l3 2",
  compare: "M8 4H4v16h4M16 4h4v16h-4M9 8l-3 4 3 4M15 8l3 4-3 4M6 12h12",
  settings:
    "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8ZM9 3h6l1 3 3 1 2 5-2 5-3 1-1 3H9l-1-3-3-1-2-5 2-5 3-1 1-3Z",
  sun: "M12 3V1m0 22v-2M3 12H1m22 0h-2M4.2 4.2l1.5 1.5m12.6 12.6 1.5 1.5m0-15.6-1.5 1.5M5.7 18.3l-1.5 1.5M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10Z",
  moon: "M21 13A9 9 0 0 1 11 3a9 9 0 1 0 10 10Z",
  search: "M21 21l-5-5M10 3a7 7 0 1 0 0 14 7 7 0 0 0 0-14Z",
  check: "m5 12 4 4L19 6",
  close: "m6 6 12 12M6 18 18 6",
  spark: "m12 2 3 7 7 3-7 3-3 7-3-7-7-3 7-3 3-7Z",
  people:
    "M16 21v-3a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v3M9 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8Zm8 0a4 4 0 0 1 0 8m2 4a4 4 0 0 1 3 4v2",
  chart: "M4 20V10m8 10V4m8 16v-7M2 22h20",
  network: "M9 2h6v6H9zM3 16h6v6H3zM15 16h6v6h-6zM12 8v5M6 16v-3h12v3",
  "badge-check":
    "M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.77 4 4 0 0 1 0 6.76 4 4 0 0 1-4.77 4.77 4 4 0 0 1-6.76 0 4 4 0 0 1-4.77-4.78 4 4 0 0 1 0-6.76ZM9 12l2 2 4-4",
  shield: "m12 2 9 4v6c0 6-9 10-9 10S3 18 3 12V6l9-4Zm-4 10 3 3 5-6",
  chat: "M21 11a9 9 0 0 1-9 9 10 10 0 0 1-4-1l-6 3 2-6a9 9 0 1 1 17-5ZM8 10h8M8 14h5",
  download: "M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4",
  edit: "m15 4 5 5M3 21l5-1L21 7l-5-5L3 15v6Z",
  copy: "M8 8h13v13H8zM16 8V3H3v13h5",
  trash: "M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7",
  upload: "M12 16V3m-5 5 5-5 5 5M4 16v5h16v-5",
  info: "M12 11v6m0-10v.01M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Z",
  refresh:
    "M3 10a9 9 0 0 1 15-6l3 3m0-5v5h-5M21 14a9 9 0 0 1-15 6l-3-3m0 5v-5h5",
  logout: "M9 3H3v18h6m6-14 5 5-5 5M8 12h12",
  menu: "M3 6h18M3 12h18M3 18h18",
  eye: "M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Zm10-3a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z",
  globe:
    "M2 12h20M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm0 0c-6 5-6 15 0 20 6-5 6-15 0-20Z",
  clock: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm0 4v6l4 2",
  heart: "M12 21 3 12a6 6 0 0 1 9-8 6 6 0 0 1 9 8l-9 9Z",
};
export function Icon({
  name,
  size = 20,
  className = "",
}: {
  name: string;
  size?: number;
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      <path d={paths[name] || paths.spark} />
    </svg>
  );
}
export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <Link href="/" className="brand" aria-label="Buyora home">
      <span className="brand-mark" />
      {!compact && (
        <span>
          buyora<span className="brand-dot">.</span>
        </span>
      )}
    </Link>
  );
}
export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={`badge ${tone}`}>{children}</span>;
}
export function Avatar({
  persona,
  small = false,
}: {
  persona: Persona;
  small?: boolean;
}) {
  const images: Record<string, string> = {
    cod: "/avatar-01.png",
    budget: "/avatar-04.png",
    skeptic: "/avatar-03.png",
    impulse: "/avatar-02.png",
    gift: "/avatar-06.png",
    office: "/avatar-02.png",
    bargain: "/avatar-01.png",
    repeat: "/avatar-06.png",
  };
  const fallback: Record<string, string> = {
    blue: "/avatar-01.png",
    mint: "/avatar-02.png",
    lavender: "/avatar-03.png",
    peach: "/avatar-04.png",
    rose: "/avatar-06.png",
    sand: "/avatar-02.png",
  };
  return (
    <span
      className={`avatar ${persona.color} ${small ? "small" : ""}`}
      aria-hidden="true"
    >
      <Image
        src={images[persona.id] || fallback[persona.color] || "/avatar-01.png"}
        alt=""
        width={72}
        height={72}
        sizes={small ? "36px" : "72px"}
      />
    </span>
  );
}
export function ButtonLink({
  href,
  children,
  secondary = false,
  className = "",
}: {
  href: string;
  children: ReactNode;
  secondary?: boolean;
  className?: string;
}) {
  return (
    <Link
      className={`button ${secondary ? "secondary" : "primary"} ${className}`}
      href={href}
    >
      {children}
    </Link>
  );
}
export function PageHeading({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description?: string;
  children?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <div className="breadcrumb">
          Workspace <Icon name="chevron" size={12} /> {eyebrow}
        </div>
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      <div className="heading-actions">{children}</div>
    </div>
  );
}
export function EmptyState({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <span className="empty-icon">
        <Icon name="box" size={28} />
      </span>
      <h3>{title}</h3>
      <p>{description}</p>
      {children}
    </div>
  );
}
export function Notice({
  children,
  tone = "",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return (
    <div className={`notice ${tone}`}>
      <Icon name="info" size={17} />
      <div>{children}</div>
    </div>
  );
}

export function ThemeToggle() {
  const [dark, setDark] = useState(false);
  useEffect(() => {
    const sync = () =>
      setDark(document.documentElement.dataset.theme === "dark");
    sync();
    const observer = new MutationObserver(sync);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });
    return () => observer.disconnect();
  }, []);
  return (
    <button
      className="icon-button"
      aria-label={`Switch to ${dark ? "light" : "dark"} mode`}
      onClick={() => {
        const theme = dark ? "light" : "dark";
        document.documentElement.dataset.theme = theme;
        try {
          localStorage.setItem("buyora-theme", theme);
        } catch {
          /* Theme still works without storage. */
        }
      }}
    >
      <Icon name={dark ? "sun" : "moon"} size={19} />
    </button>
  );
}

const ToastContext = createContext<(message: string) => void>(() => {});
export const useToast = () => useContext(ToastContext);
export function Providers({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState("");
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );
  const show = (message: string) => {
    if (timer.current) clearTimeout(timer.current);
    setToast(message);
    timer.current = setTimeout(() => setToast(""), 4500);
  };
  return (
    <ToastContext value={show}>
      {children}
      <div
        className={`toast ${toast ? "visible" : ""}`}
        role="status"
        aria-live="polite"
      >
        <Icon name="check" size={18} />
        {toast}
      </div>
    </ToastContext>
  );
}

export function Modal({
  title,
  children,
  onClose,
  wide = false,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    dialog?.showModal();
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      dialog?.close();
      document.body.style.overflow = previous;
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className={`modal ${wide ? "wide" : ""}`}
      onCancel={onClose}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      aria-labelledby="modal-title"
    >
      <div className="modal-inner">
        <div className="modal-heading">
          <h2 id="modal-title">{title}</h2>
          <button
            className="icon-button"
            onClick={onClose}
            aria-label="Close dialog"
          >
            <Icon name="close" />
          </button>
        </div>
        {children}
      </div>
    </dialog>
  );
}

export function ProductArt({
  product,
  className = "",
}: {
  product: Pick<Product, "art" | "image" | "name">;
  className?: string;
}) {
  const artId = useId().replaceAll(":", "");
  const gradientId = `fabric-${artId}`;
  const shadowId = `art-shadow-${artId}`;
  if (product.image)
    return (
      <div className={`product-art ${className}`}>
        {/* Uploaded images are browser-local data URLs; no optimization server is needed. */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={product.image} alt={product.name} />
      </div>
    );
  return (
    <div
      className={`product-art art-${product.art} ${className}`}
      aria-label={`${product.name}, illustrative placeholder`}
      role="img"
    >
      <svg viewBox="0 0 320 280" aria-hidden="true">
        <defs>
          <linearGradient id={gradientId} x1="0" x2="1" y1="0" y2="1">
            <stop stopColor={product.art === "kurta" ? "#b5c5c4" : "#e6ddc9"} />
            <stop
              offset="1"
              stopColor={product.art === "kurta" ? "#718c8b" : "#c7bca1"}
            />
          </linearGradient>
          <filter id={shadowId}>
            <feGaussianBlur stdDeviation="9" />
          </filter>
        </defs>
        <ellipse
          cx="160"
          cy="242"
          rx="74"
          ry="10"
          fill="#384b53"
          opacity=".13"
          filter={`url(#${shadowId})`}
        />
        {product.art === "audio" ? (
          <g transform="rotate(-12 160 140)">
            <rect
              x="83"
              y="116"
              width="154"
              height="105"
              rx="42"
              fill="#f6f8f8"
              stroke="#ced9de"
              strokeWidth="2"
            />
            <path d="M84 154h152" fill="none" stroke="#ced9de" />
            <circle cx="160" cy="185" r="3" fill="#7ea6a4" />
            <g fill="#f9fcfc" stroke="#c8d4db" strokeWidth="2">
              <path d="M114 59c-25 0-25 39 0 39h10v34c0 15 19 15 19 0V78c0-12-10-19-29-19Z" />
              <path d="M206 59c25 0 25 39 0 39h-10v34c0 15-19 15-19 0V78c0-12 10-19 29-19Z" />
            </g>
            <path
              d="M113 70v14m94-14v14"
              stroke="#637982"
              strokeWidth="5"
              strokeLinecap="round"
            />
          </g>
        ) : product.art === "kurta" ? (
          <g>
            <path
              d="m121 46-42 21-32 76 33 16 20-41-7 117h135l-8-117 21 41 33-16-33-76-42-21Z"
              fill={`url(#${gradientId})`}
            />
            <path d="M140 46q20 21 40 0l-8 23h-24Z" fill="#4c7070" />
            <path d="M160 67v61" stroke="#d6e0db" strokeWidth="3" />
            <path
              d="M150 77h20m-20 12h20m-20 12h20"
              stroke="#d6e0db"
              strokeWidth="1"
            />
            <path d="M99 223h124" stroke="#617f7c" strokeDasharray="3 3" />
          </g>
        ) : (
          <g transform="rotate(-8 160 145)">
            <path
              d="M105 102V78a55 55 0 0 1 110 0v24"
              fill="none"
              stroke="#b5a98d"
              strokeWidth="14"
            />
            <path
              d="M105 102V78a55 55 0 0 1 110 0v24"
              fill="none"
              stroke="#ded4bc"
              strokeWidth="9"
            />
            <path
              d="m74 95 9 130q1 14 17 15h123q15-1 16-15l9-130Z"
              fill={`url(#${gradientId})`}
            />
            <path
              d="m86 105 8 116q0 8 9 8h118q8 0 8-8l8-116"
              fill="none"
              stroke="#a89b7d"
              strokeDasharray="2 3"
              opacity=".55"
            />
            <path d="M107 96v34m107-34v34" stroke="#b4a78a" strokeWidth="12" />
            <text
              x="160"
              y="171"
              textAnchor="middle"
              fill="#466d80"
              className="art-wordmark"
              fontFamily="Georgia, serif"
              letterSpacing="5"
            >
              nila
            </text>
            <text
              x="160"
              y="187"
              textAnchor="middle"
              fill="#6c7d7f"
              className="art-tagline"
              letterSpacing="2"
            >
              MADE FOR EVERYDAY
            </text>
          </g>
        )}
      </svg>
    </div>
  );
}

export function ScoreRing({
  score,
  label,
  large = false,
  progress = 1,
}: {
  score: number;
  label?: string;
  large?: boolean;
  progress?: number;
}) {
  return (
    <div className={`score-ring ${large ? "large" : ""}`}>
      <svg viewBox="0 0 100 100" aria-hidden="true">
        <circle cx="50" cy="50" r="43" className="ring-track" />
        <circle
          cx="50"
          cy="50"
          r="43"
          className="ring-value"
          strokeDasharray={`${score * Math.min(1, Math.max(0, progress)) * 2.7} 270`}
        />
      </svg>
      <div>
        <strong>
          <CountUp value={score} progress={progress} />
        </strong>
        <span>{label || "out of 100"}</span>
      </div>
    </div>
  );
}
export function Field({
  label,
  hint,
  children,
  className = "",
}: {
  label: string;
  hint?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <label className={`field ${className}`}>
      <span>{label}</span>
      {children}
      {hint && <small>{hint}</small>}
    </label>
  );
}
