import { useEffect, useRef, type ReactNode } from "react";

interface SheetProps {
  label: string;
  onClose: () => void;
  children: ReactNode;
}

// Bottom sheet: closes on Escape and on a backdrop tap; focus moves in and goes back to the
// element that opened it.
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
      <section ref={sheetRef} className="sheet" role="dialog" aria-modal="true" aria-label={label} tabIndex={-1}>
        {children}
      </section>
    </div>
  );
}
