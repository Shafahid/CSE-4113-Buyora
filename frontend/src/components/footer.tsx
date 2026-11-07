import Link from "next/link";
import { Brand, Icon } from "./ui";
import styles from "./footer.module.css";

export function Footer({ compact = false }: { compact?: boolean }) {
  return (
    <footer className={`${styles.footer} ${compact ? styles.compact : ""}`}>
      <div className={styles.content}>
        <div className={styles.brandBlock}>
          <Brand />
          <p>
            A second perspective
            <br />
            before your next post goes live.
          </p>
          {!compact && (
            <span>
              <Icon name="globe" size={15} />
              Built for Bangladesh’s social commerce sellers.
            </span>
          )}
        </div>
        <nav
          aria-label={
            compact ? "Workspace footer navigation" : "Footer navigation"
          }
          className={styles.navigation}
        >
          <div>
            <h2>Explore Buyora</h2>
            <Link href="/simulate">Run a simulation</Link>
            <Link href="/reports/sample-1?view=spread">
              Explore a sample report
            </Link>
            {!compact && <Link href="/#how-it-works">How it works</Link>}
          </div>
          <div>
            <h2>Your workspace</h2>
            <Link href="/dashboard">Overview</Link>
            <Link href="/products">Products & posts</Link>
            <Link href="/history">Simulation history</Link>
            {!compact && <Link href="/compare">Compare reports</Link>}
          </div>
          {!compact && (
            <div>
              <h2>Make it yours</h2>
              <Link href="/settings">Settings & data</Link>
              <Link href="/login">Sign in to demo</Link>
              <Link href="/register">Create demo profile</Link>
            </div>
          )}
        </nav>
      </div>
      <div className={styles.bottom}>
        <span>© 2026 Buyora. Made for thoughtful selling.</span>
      </div>
    </footer>
  );
}
