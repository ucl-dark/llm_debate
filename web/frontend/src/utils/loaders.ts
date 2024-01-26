export async function debateLoader({ params }) {
  try {
    const { debate_id } = params;
    const response = await fetch(`/api/debates/${debate_id}`);
    if (!response.ok) {
      return response.json().then((error) => {
        throw new Error(`HTTP Error: ${response.status} - ${error.detail}`);
      });
    }
    const debate = await response.json();
    return { debate };
  } catch (error) {
    console.error("Error:", error);
  }
}
