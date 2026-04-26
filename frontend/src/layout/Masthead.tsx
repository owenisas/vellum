import { Link, NavLink } from "react-router-dom";
import { LiveTicker } from "../components/ui/LiveTicker";
import { useAuth } from "../auth/useAuth";
import { cn } from "../lib/cn";
import styles from "./Masthead.module.css";

const NAV = [
  { to: "/studio", label: "Studio" },
  { to: "/ledger", label: "Ledger" },
  { to: "/principles", label: "Principles" },
];

export function Masthead() {
  const { isAuthenticated, user, logout } = useAuth();
  return (
    <header className={styles.bar}>
      <div className={styles.inner}>
        <Link to="/" className={styles.brand} aria-label="Vellum — return to cover">
          <span className={styles.brandMark}>VELLUM</span>
          <span className={styles.brandIssue}>VOL.01 · ISSUE 01 · PROVENANCE</span>
        </Link>
        <nav className={styles.nav} aria-label="Primary">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              className={({ isActive }) => cn(styles.link, "link-u", isActive && styles.active)}
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className={styles.right}>
          <span className={styles.tickerWrap}><LiveTicker /></span>
          {isAuthenticated && user?.email ? (
            <button className={styles.auth} onClick={() => logout()} title={user.email}>
              <span className={styles.authDot} aria-hidden />
              <span>Sign out</span>
            </button>
          ) : null}
        </div>
      </div>
    </header>
  );
}
