import { useCallback } from "react";
import { useLocation } from "react-router-dom";

const useCreatePlaygroundDebate = () => {
  const location = useLocation();

  const createNewDebate = useCallback(
    async (debateType: string, config: string, previousDebateId?: number) => {
      try {
        const response = await fetch("/api/playground/debates", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            debate_type: debateType,
            config_path: config,
            previous_debate_id: previousDebateId,
          }),
        });

        if (!response.ok) {
          throw new Error("Network response was not ok");
        }

        const data = await response.json();
        // This is better than react-router's navigate because it does a full page load, avoiding stale state
        window.location.href = `/playground/debates/${data.id}${location.search}`;
      } catch (error) {
        console.error("There was a problem with the fetch operation:", error);
        throw error
      }
    },
    [location],
  );

  return createNewDebate;
};

export default useCreatePlaygroundDebate;
