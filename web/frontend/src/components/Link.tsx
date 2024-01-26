import { Link as RouterLink, useSearchParams } from "react-router-dom";

// Upgraded version of Link that preserves search params
const Link = ({ to, ...props }) => {
  const [searchParams] = useSearchParams();

  // If 'to' is an object with a 'pathname' property, add search params to it
  // If 'to' is just a string path, convert it to an object and add search params
  const toWithSearchParams =
    typeof to === "string"
      ? { pathname: to, search: searchParams.toString() }
      : { ...to, search: searchParams.toString() };

  return <RouterLink to={toWithSearchParams} {...props} />;
};

export default Link;
