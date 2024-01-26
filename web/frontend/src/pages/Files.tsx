import { useLoaderData } from "react-router-dom";
import { parseISO, format } from "date-fns";
import Link from "../components/Link";
import { Disclosure } from "@headlessui/react";
import { ChevronDownIcon } from "@heroicons/react/24/outline";
import { AuthRequirement, useUser } from "../hooks/userProvider";

export async function filesLoader() {
  try {
    const response = await fetch("/api/files");
    const files = await response.json();
    return { files };
  } catch (error) {
    console.error("Error:", error);
  }
}

type File = {
  id: number;
  path: string;
  path_hash: string;
  row_count: number;
  created_at: string;
  imported_at: string;
};

type FileTree = {
  [key: string]: FileTree | File;
};

function createTree(files: File[]): FileTree {
  const tree: FileTree = {};

  files.forEach((file) => {
    // Trim beginning /
    const path = file.path.startsWith("/") ? file.path.slice(1) : file.path;
    const pathParts = path.split("/");
    let currentLevel = tree;

    pathParts.forEach((part, index) => {
      if (index === pathParts.length - 1) {
        currentLevel[part] = file;
      } else if (!currentLevel[part]) {
        currentLevel[part] = {};
      }

      if (
        typeof currentLevel[part] === "object" &&
        !("path" in currentLevel[part])
      ) {
        currentLevel = currentLevel[part] as FileTree;
      }
    });
  });

  return tree;
}

const formatDate = (timestamp: string) => {
  const date = parseISO(timestamp);
  return format(date, "MMMM do yyyy");
};

const isDirectory = (treeNode: FileTree | File) => {
  return typeof treeNode === "object" && !("path" in treeNode);
};

function DirectoryTree({ tree, path = "" }: { tree: FileTree; path?: string }) {
  const dirs = Object.keys(tree).filter((key) => isDirectory(tree[key]));
  const files = Object.keys(tree).filter((key) => !isDirectory(tree[key]));
  return (
    <div className="mt-2 flex flex-col space-y-2">
      {dirs.map((key) => (
        <div key={key}>
          <Disclosure>
            {({ open }) => (
              <div className="pl-2 pr-2">
                <Disclosure.Button className="flex justify-between w-full rounded px-4 py-2 text-sm font-medium text-left text-black bg-blue-100 hover:bg-blue-200 focus:outline-none focus-visible:ring focus-visible:ring-blue-500 focus-visible:ring-opacity-75">
                  <div>
                    <span className="text-gray-500 mr-4">
                      {Object.keys(tree[key]).length}
                    </span>
                    <span>{key}</span>
                  </div>
                  <ChevronDownIcon
                    className={`${open ? "transform rotate-180" : ""
                      } w-5 h-5 text-black`}
                  />
                </Disclosure.Button>
                <Disclosure.Panel className="px-2  text-sm text-gray-500">
                  <DirectoryTree
                    tree={tree[key] as FileTree}
                    path={`${path}/${key}`}
                  />
                </Disclosure.Panel>
              </div>
            )}
          </Disclosure>
        </div>
      ))}
      <div>
        {files.length > 0 && (
          <div className="w-full flex justify-end pr-4">
            <span>Created on</span>
          </div>
        )}
        {files.map((key) => (
          <div key={key}>
            <Link
              to={`/files/${(tree[key] as File).path_hash.slice(0, 8)}`}
              className="block px-4 py-2 text-sm text-black hover:bg-gray-200 flex justify-between"
            >
              <div>
                <span className="mr-4 text-gray-500">
                  {(tree[key] as File).row_count}
                </span>
                <span>{key}</span>
              </div>
              <span>{formatDate((tree[key] as File).created_at)}</span>
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
}
function getRootAndFirstBranches(tree: FileTree, maxDepth = 1000) {
  let root = "/";
  let currentNode = tree;
  let depth = 0;

  while (depth < maxDepth) {
    const entries = Object.entries(currentNode);
    if (entries.length > 1 || !isDirectory(currentNode)) {
      return [root, currentNode];
    }
    const [dirName, dir] = entries[0];
    if (!isDirectory(dir)) {
      return [root, currentNode];
    }
    root = root.concat(`${dirName}/`);
    currentNode = dir;
    depth++;
  }
  console.warn("No branching node found");
  return [null, null];
}

function Files() {
  useUser(AuthRequirement.Admin)
  const { files } = useLoaderData();
  if (!files.length) {
    return <div className="px-8 py-4">No files found.</div>;
  }
  let tree = createTree(files);
  const [root, firstBranchingNode] = getRootAndFirstBranches(tree);
  return (
    <div className="">
      {files && files.length && <DirectoryTree tree={firstBranchingNode} />}
      <div className="px-8 py-4 text-bold text-sm text-gray-500">
        Root data dir: {root}
      </div>
    </div>
  );
}

export default Files;
