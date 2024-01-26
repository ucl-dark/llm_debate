import { ReactNode, createContext, useContext, useState } from "react";

type DebateContextType = {
  generatingTurn: boolean;
  setGeneratingTurn: React.Dispatch<React.SetStateAction<boolean>>;
};

const defaultDebateContext: DebateContextType = {
  generatingTurn: false,
  setGeneratingTurn: () => { },
};

const DebateContext = createContext<DebateContextType>(defaultDebateContext);

export const useDebateContext = () => {
  const context = useContext(DebateContext);

  if (!context) {
    throw new Error("Must be inside a DebateProvider");
  }

  return context;
};

export const DebateProvider = ({ children }: { children: ReactNode }) => {
  const [generatingTurn, setGeneratingTurn] = useState<boolean>(false);

  return (
    <DebateContext.Provider value={{ generatingTurn, setGeneratingTurn }}>
      {children}
    </DebateContext.Provider>
  );
};
