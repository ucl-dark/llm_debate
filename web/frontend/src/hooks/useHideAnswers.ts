import { useSearchParams } from "react-router-dom";

const useHideAnswers = (): [() => boolean, () => void] => {
  const [searchParams, setSearchParams] = useSearchParams();

  // Getter: getHideAnswers function
  const getHideAnswers = (): boolean => {
    return searchParams.get("hideAnswers") === "true";
  };

  // Setter: toggleHideAnswers function
  const toggleHideAnswers = (): void => {
    const currentHideAnswers = getHideAnswers();
    const newHideAnswers = !currentHideAnswers;
    setSearchParams({ hideAnswers: newHideAnswers.toString() });
  };

  return [getHideAnswers, toggleHideAnswers];
};

export default useHideAnswers;
