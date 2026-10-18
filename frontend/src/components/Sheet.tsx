import { useEffect, useRef, type KeyboardEvent as ReactKeyboardEvent, type ReactNode } from "react";

const FOCUSABLE =
  'button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])';

// Keeps Tab and Shift+Tab inside a modal dialog: past the last control it wraps to the first and back.
export function trapTab(event: ReactKeyboardEvent<HTMLElement>): void {
  if (event.key !== "Tab") {
    return;
  }
  const dialog = event.currentTarget;
  const focusable = dialog.querySelectorAll<HTMLElement>(FOCUSABLE);
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  const active = document.activeElement;
  if (!first) {
    event.preventDefault();
  } else if (event.shiftKey && (active === first || active === dialog)) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && active === last) {
    event.preventDefault();
    first.focus();
  }
}

interface SheetProps {
  label: string;
  onClose: () => void;
  children: ReactNode;
}

// Bottom sheet: closes on Escape and on a backdrop tap; focus moves in, stays in while Tab cycles,
// and goes back to the element that opened it.
export function Sheet({ label, onClose, children }: SheetProps): JSX.Element {
  const sheetRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    sheetRef.current?.focus();
    return () => opener?.focus();
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div
      className="sheet-backdrop"
      role="presentation"
      onClick={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <section ref={sheetRef} className="sheet" role="dialog" aria-modal="true" aria-label={label}
        tabIndex={-1}
        onKeyDown={trapTab}
      >
        {children}
      </section>
    </div>
  );
}
