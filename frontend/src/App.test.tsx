import { render, screen } from "@testing-library/react";

import { App } from "./App";

describe("App", () => {
  it("renders the phase-one scaffold message", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "Admin UI scaffold is ready." })).toBeInTheDocument();
  });
});
